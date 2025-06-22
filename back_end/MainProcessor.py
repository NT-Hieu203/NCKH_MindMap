from PDF_Processor import *
from RunBuildTree import *
from CreateOnology import *
import time
def process_PDF_file(client, model_embedding, model_detect_layout, reader, PDF_file_path):
    '''
    Tạo ra cây phân cấp từ file PDF.
    Args:
        PDF_file_path: đường dẫn đến file PDF trong thư mục upload

    Returns:
        list các dict có index và parent_index để tạo cây
    '''
    pdf_result = process_full_pdf(model_detect_layout, reader, PDF_file_path)
    s_time = time.time()
    merged_result = merge_short_paragraphs(pdf_result['all_paragraphs'])
    e_time = time.time()
    print(f"Thời gian merge: {e_time - s_time}s")

    result = run_clustering_with_tree_building(client, model_embedding, merged_result, clustering_strategy='adaptive')
    clustering_tree = result['tree']
    return clustering_tree

def create_ontology(model_embedding, merged_nodes, save_path, ontology_iri):
    """
    Tạo ontology dựa vào cấu trúc index và index_parent từ merged_nodes.
    Thêm annotation 'summary' cho mỗi class.

    Args:
        merged_nodes: List các node đã được xử lý từ hàm merge_short_nodes
        ontology_iri: IRI của ontology

    Returns:
        Đối tượng ontology đã được tạo
    """
    # Tạo ontology mới
    onto = get_ontology(ontology_iri)

    # Dictionary để lưu trữ class_name theo index
    class_names = {}

    # Bước 1: Duyệt qua các node để lấy và làm sạch tên class
    for node in merged_nodes:
        index = node["index"]
        # Đảm bảo bạn đang truy cập đúng khóa dữ liệu
        keyword = node.get("keyword") # Sử dụng .get() để an toàn hơn
        class_name = keyword if keyword else node["text"]

        # Làm sạch tên class để phù hợp với quy ước đặt tên trong ontology
        class_name = clean_class_name(class_name)
        class_names[index] = class_name

    # Bước 2: Tạo annotation properties
    with onto:
        safe_add_annotation_property(onto, "summary")
        safe_add_annotation_property(onto, "summary_embeddings")

    # Bước 3: Xác định và tạo root class
    root_node_info = None
    for node in merged_nodes:
        # Kiểm tra cả type và parent_index = -1 để xác định root node
        if node.get("type") == "root_node" and node.get("parent_index") == -1:
            root_node_info = node
            break

    main_root_class = None
    if root_node_info:
        # Nếu tìm thấy root_node, sử dụng nó làm root của ontology
        root_class_name = class_names[root_node_info["index"]]
        with onto:
            main_root_class = types.new_class(root_class_name, (Thing,))
            # Thêm summary và summary_embeddings cho root_class
            add_annotation_to_class(onto,model_embedding, main_root_class, root_node_info, merged_nodes)

        # Đặt index của root_node làm parent_index để các node con của nó được xử lý
        initial_parent_to_process = root_node_info["index"]
    else:
        # Fallback về "Lịch_sử_Việt_Nam" nếu không có root_node nào được đánh dấu phù hợp
        with onto:
            main_root_class = types.new_class("Lịch_sử_Việt_Nam", (Thing,))

        # Nếu không có root_node đặc biệt, các node có parent_index là -1 hoặc None sẽ là con của "Lịch_sử_Việt_Nam"
        initial_parent_to_process = -1 # Hoặc None, tùy theo cách bạn muốn nhóm các node không cha

    # Bước 4: Xử lý các node theo từng cấp độ
    nodes_by_parent = group_nodes_by_parent(merged_nodes)
    # pri = json.dumps(nodes_by_parent, indent=4)
    # print(pri)

    # Bắt đầu xử lý từ các node mà parent_index của chúng là `initial_parent_to_process`
    # (hoặc các node có parent_index là -1/None nếu không có root_node đặc biệt)
    # Các node này sẽ được gắn vào `main_root_class`

    # Lấy danh sách các node con trực tiếp của `initial_parent_to_process`
    # Đây là các node sẽ được thêm vào dưới `main_root_class`
    first_level_children = nodes_by_parent.get(initial_parent_to_process, [])

    for node in first_level_children:
        # Nếu node hiện tại là root_node đã được xử lý (tránh xử lý lại chính nó), bỏ qua
        if root_node_info and node["index"] == root_node_info["index"]:
            continue

        index = node["index"]
        class_name = class_names[index]
        parent_class_name = main_root_class.name # Gán cho main_root_class đã tạo

        class_name_list = [class_name]
        # Thêm class con vào ontology, gắn nó với main_root_class
        add_class_to_ontology(onto,model_embedding, parent_class_name, class_name_list, node, merged_nodes)
        class_names[index] = class_name_list[0] # Cập nhật tên nếu có thay đổi

        # Đệ quy xử lý các node con của node hiện tại
        process_nodes_level_by_level(onto, model_embedding, nodes_by_parent, class_names, merged_nodes, index)

    onto.save(save_path)

    return onto