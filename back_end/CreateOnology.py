from owlready2 import *
import types
import re
import numpy as np
from LLMquery import get_embedding

def convert_embedding_to_string(embedding_matrix: np.ndarray) -> str:
    """
    Chuyển đổi một ma trận embedding (numpy.ndarray) thành một chuỗi
    biểu diễn list lồng hai cấp theo cú pháp Python.

    Args:
        embedding_matrix: Ma trận embedding được encode từ model (numpy.ndarray).
                          Có thể là 1D vector (sẽ được coi là ma trận 1 hàng)
                          hoặc 2D ma trận (nhiều hàng, mỗi hàng là một vector embedding).

    Returns:
        Một chuỗi định dạng list lồng hai cấp, ví dụ:
        "[[0.123, 0.456, -0.789], [-0.987, 0.654, 0.321]]"
    """
    if not isinstance(embedding_matrix, np.ndarray):
        raise TypeError("Input must be a numpy.ndarray.")

    # Đảm bảo mảng là ít nhất 2 chiều để tạo list lồng hai cấp
    # Nếu là 1D vector, reshape thành (1, D)
    if embedding_matrix.ndim == 1:
        matrix_to_convert = embedding_matrix.reshape(1, -1)
    elif embedding_matrix.ndim == 2:
        matrix_to_convert = embedding_matrix
    else:
        raise ValueError("Embedding matrix must be 1D or 2D.")

    # Chuyển NumPy array sang list của list Python
    list_of_lists = matrix_to_convert.tolist()
    return str(list_of_lists)

def safe_add_annotation_property(onto, annotation_name):
    """Tạo annotation property nếu chưa tồn tại."""
    with onto:
        if not hasattr(onto, annotation_name):
            print(f"Tạo annotation property mới: {annotation_name}")
            NewAnnotation = types.new_class(annotation_name, (AnnotationProperty,))
            setattr(onto, annotation_name, NewAnnotation)

def add_annotation_to_entity(onto, entity_name, annotation_name, annotation_value, save_path=None, save_ontology=False):
    """Thêm annotation cho một entity trong ontology."""
    try:
        entity = onto[entity_name]  # Lấy entity từ ontology
        safe_add_annotation_property(onto, annotation_name)

        # GÁN TRỰC TIẾP GIÁ TRỊ (Không append!)
        setattr(entity, annotation_name, annotation_value)

        # Lưu ontology nếu cần
        if save_ontology:
            save_target = save_path if save_path else "/content/MindMap.owl"
            onto.save(file=save_target, format="rdfxml")
            print(f"Đã lưu ontology tại {save_target}.")

        print(f"Đã thêm annotation '{annotation_name}' với giá trị '{annotation_value}' cho entity '{entity_name}'.")

    except KeyError:
        print(f"Entity '{entity_name}' không tồn tại trong ontology.")


def group_nodes_by_parent(merged_nodes):
    """
    Nhóm các node theo index của parent.

    Args:
        merged_nodes: Danh sách các node đã được xử lý.

    Returns:
        Một dictionary, trong đó key là parent_index và value là danh sách các node có cùng parent_index đó.
    """
    nodes_by_parent = {}
    for node in merged_nodes:
        # Sử dụng 'parent_index' thay vì 'index_parent' nếu dữ liệu của bạn có key là 'parent_index'
        # Đảm bảo rằng key này tồn tại hoặc xử lý trường hợp None
        parent_index = node.get("parent_index")

        # Nếu parent_index là None, có thể bạn muốn nhóm chúng vào một key riêng biệt
        # hoặc coi chúng như các node gốc (tôi sẽ coi None như -1 ở đây cho nhất quán)
        if parent_index is None:
            parent_index = -1

        if parent_index not in nodes_by_parent:
            nodes_by_parent[parent_index] = []
        nodes_by_parent[parent_index].append(node)

    return nodes_by_parent

def process_nodes_level_by_level(onto, model_embedding, nodes_by_parent, class_names, merged_nodes, parent_index):
    """
    Xử lý các node theo từng cấp độ, bắt đầu từ một parent_index cụ thể.

    Args:
        onto: Đối tượng ontology.
        nodes_by_parent: Dictionary chứa các node được nhóm theo parent_index.
        class_names: Dictionary lưu trữ class_name theo index.
        parent_index: Index của parent đang được xử lý.
        merged_nodes: Danh sách các node đã được xử lý (để lấy thông tin summary).
    """
    current_level_nodes = nodes_by_parent.get(parent_index, [])
    for node in current_level_nodes:
        index = node["index"]
        class_name = class_names[index]

        # Đảm bảo parent_index có trong class_names trước khi truy cập
        if parent_index in class_names:
            parent_class_name = class_names[parent_index]
        else:
            # Điều này xảy ra nếu parent_index là -1 hoặc một index không hợp lệ khác
            # và nó không phải là root_node được xử lý đặc biệt.
            # Trong trường hợp này, chúng ta cần tìm cách gắn nó vào một parent hợp lệ,
            # ví dụ như lớp Thing hoặc lớp root của ontology.
            # Với cấu trúc code hiện tại, nó chỉ nên được gọi cho các parent_index đã có trong class_names
            # hoặc cho các node con trực tiếp của main_root_class
            print(f"Warning: Parent index {parent_index} not found in class_names. Setting parent to Thing.")
            parent_class_name = "Thing" # Fallback

        class_name_list = [class_name]
        add_class_to_ontology(onto, model_embedding, parent_class_name, class_name_list, node, merged_nodes)
        class_names[index] = class_name_list[0] # Cập nhật tên class nếu có thay đổi

        # Đệ quy xử lý các node con
        process_nodes_level_by_level(onto, model_embedding, nodes_by_parent, class_names, merged_nodes, index)

def add_class_to_ontology(onto, model_embedding, parent_class_name, class_name_list, node, merged_nodes):
    """
    Thêm một class vào ontology, kiểm tra trùng lặp và tạo quan hệ cha-con.
    Thêm annotation 'summary' cho class.

    Args:
        onto: Đối tượng ontology.
        parent_class_name: Tên của class cha.
        class_name_list: List chứa tên của class cần thêm (để có thể thay đổi nếu trùng).
        node: Node hiện tại đang được xử lý.
        merged_nodes: Danh sách các node đã được xử lý (để lấy thông tin summary).
    """
    class_name = class_name_list[0]
    with onto:
        parent_class = getattr(onto, parent_class_name, None)
        if not parent_class:
            # Nếu không tìm thấy parent_class, nó có thể là Thing hoặc một class nào đó chưa được tạo
            # Điều này chỉ nên xảy ra nếu parent_class_name là "Thing" hoặc nếu có lỗi logic
            # Với "Thing", nó sẽ được tạo nếu chưa có
            parent_class = types.new_class(parent_class_name, (Thing,))

        # Kiểm tra và xử lý trùng tên class
        if getattr(onto, class_name, None):
            i = 1
            while True:
                new_class_name = f"{class_name}{'_'*i}"
                if not getattr(onto, new_class_name, None):
                    class_name_list[0] = new_class_name
                    break
                i += 1

        new_class = types.new_class(class_name_list[0], (parent_class,))
        add_annotation_to_class(onto, model_embedding, new_class, node, merged_nodes)


def add_annotation_to_class(onto, model_embedding, owl_class, node, merged_nodes):
    """
    Thêm annotation 'summary' và 'summary_embeddings' cho một class.
    """
    # Đảm bảo các annotation property tồn tại
    summary_prop = getattr(onto, "summary", None)
    if summary_prop is None:
        summary_prop = types.new_class("summary", (AnnotationProperty,))
        onto.summary = summary_prop

    summary_embeddings_prop = getattr(onto, "summary_embeddings", None)
    if summary_embeddings_prop is None:
        summary_embeddings_prop = types.new_class("summary_embeddings", (AnnotationProperty,))
        onto.summary_embeddings = summary_embeddings_prop

    summary_value = node.get("summarized_paragraph") # Đảm bảo key này đúng
    if summary_value:
        try:
            summary_embedding = get_embedding(model_embedding, summary_value)
            owl_class.summary = summary_value
            owl_class.summary_embeddings = convert_embedding_to_string(summary_embedding)
        except NameError:
            print("Hàm get_embedding chưa được định nghĩa")
            owl_class.summary = summary_value


def clean_class_name(name):
    """
    Làm sạch tên class để phù hợp với quy ước đặt tên trong ontology.

    Args:
        name: Tên class ban đầu

    Returns:
        Tên class đã được làm sạch
    """
    # Loại bỏ các ký tự đặc biệt trừ dấu gạch dưới và khoảng trắng
    name = re.sub(r'[^\w\s-]', '', name)

    # Thay thế khoảng trắng bằng dấu gạch dưới
    name = name.replace(' ', '_')

    # Giới hạn độ dài tên
    name = name[:200]

    # Đảm bảo tên bắt đầu bằng chữ cái hoặc dấu gạch dưới
    if name and not (name[0].isalpha() or name[0] == '_'):
        name = '_' + name

    # Nếu tên rỗng, đặt tên mặc định
    if not name:
        name = 'UnnamedClass'
    return name