

from owlready2 import *
import faiss
import numpy as np


"""**pp1**: lấy toàn bộ anotation làm chú thích
**pp2**: embedding anotation để tìm gần với câu hỏi và lấy entity đó

**Tìm tất cả các instances có anotation**
"""

def get_entities_with_annotation(onto, annotation):
    """
    Tìm tất cả các instances và classes có annotation trong ontology.

    Parameters:
    - ontology_available: Ontology đang làm việc
    - annotation: Tên annotation cần tìm

    Returns:
    - Dictionary chứa tất cả các instances và classes có annotation
    """
    result = {}
    processed_entities = set()  # Tập hợp để theo dõi các entity đã xử lý

    # Duyệt qua tất cả các lớp trong ontology
    for cls in onto.classes():
        # Kiểm tra và thêm annotation của class (nếu có và chưa xử lý)
        if cls.name not in processed_entities and hasattr(cls, annotation):
            annotation_value = getattr(cls, annotation)
            if annotation_value:  # Kiểm tra không rỗng
                # Loại bỏ các giá trị trùng lặp trong annotation_value nếu nó là list
                if isinstance(annotation_value, list):
                    # Sử dụng dict.fromkeys để loại bỏ các phần tử trùng lặp nhưng giữ thứ tự
                    unique_values = list(dict.fromkeys(tuple(x) if isinstance(x, list) else x for x in annotation_value))
                    result[cls.name] = {annotation: unique_values}
                else:
                    result[cls.name] = {annotation: annotation_value}
                processed_entities.add(cls.name)

        # Xử lý các instances
        for instance in cls.instances():
            if instance.name not in processed_entities and hasattr(instance, annotation):
                annotation_value = getattr(instance, annotation)
                if annotation_value:
                    # Loại bỏ các giá trị trùng lặp trong annotation_value nếu nó là list
                    if isinstance(annotation_value, list):
                        # Chuyển đổi các phần tử để có thể so sánh và loại bỏ trùng lặp
                        unique_values = list(dict.fromkeys(tuple(x) if isinstance(x, list) else x for x in annotation_value))
                        result[instance.name] = {annotation: unique_values}
                    else:
                        result[instance.name] = {annotation: annotation_value}
                    processed_entities.add(instance.name)
    return result


"""**===========================================================**

**Find_relation()**
"""

def find_relation(onto):
    """
    Tìm cấu trúc cây phân cấp của ontology và các instances.

    Parameters:
    - ontology_available: Ontology đang làm việc

    Returns:
    - Dictionary chứa cấu trúc cây ontology
    """
    result = {}

    # Danh sách tất cả các lớp để kiểm tra
    all_classes = list(onto.classes())
    # Tìm các top-level classes (không có superclass ngoài Thing)
    top_classes = []
    for cls in all_classes:
        # Lấy tất cả các lớp cha trực tiếp
        parents = [p for p in cls.is_a if isinstance(p, onto.Thing.__class__)]
        # Loại bỏ Thing hoặc lớp chính nó
        parents = [p for p in parents if p != onto.Thing and p != cls]

        if not parents:  # Nếu không có lớp cha nào ngoài Thing
            top_classes.append(cls)
    def build_tree(cls):
        try:
          label = cls.label[0]
          if label:
            node_name = label
          else:
            node_name = cls.name
        except:
          node_name = cls.name
        """Xây dựng cây cho một lớp cụ thể"""
        node = {"name": node_name}

        # Tìm tất cả lớp con trực tiếp
        direct_subclasses = []
        for sub in all_classes:
            if cls in sub.is_a and sub != cls:
                direct_subclasses.append(sub)

        if direct_subclasses:  # Nếu có lớp con
            node["subclasses"] = []
            for sub in direct_subclasses:
                node["subclasses"].append(build_tree(sub))
        else:  # Nếu là lớp lá (không có lớp con)
            # Tìm instances của lớp này
            instances = list(cls.instances())
            if instances:
                node["Instances"] = [inst.name for inst in instances]
        return node

    for cls in top_classes:
        result[cls.name] = build_tree(cls)

    return result


"""**PP1: lấy quan hệ và tên entity cho LLM dựa trên câu hỏi để tìm thực thể liên quan**"""

def create_explication(entities_with_annotation_sumarry : dict):
  explication = {}
  for entity, entity_value in entities_with_annotation_sumarry.items():
    for annotation, value in entity_value.items():
        full_text_information = ''.join(value)
        explication[entity] = full_text_information
  return explication


import json

def find_entities_from_question_PP1(client, relation, question, chat_history):
    messages = [
        {
            "role": "system",
            "content": """Bạn là một agent hữu ích được thiết kế để tìm tên thực thể liên quan đến câu hỏi.

            Dựa trên TÊN THỰC THỂ, CÁC QUAN HỆ TƯƠNG ỨNG, hãy xác định xem câu hỏi của người dùng có thể được trả lời bằng các thực thể đã liệt kê hay không.

            - Trích xuất các thực thể được nhắc đến trực tiếp trong câu hỏi hoặc
            - Tìm ra những thực thể phù hợp có khả năng trả lời cho câu hỏi, ngay cả khi người dùng không nhắc đến tên thực thể rõ ràng.
            - Ưu tiên các thực thể có mối liên hệ ngữ nghĩa hoặc quan hệ tri thức gần với nội dung câu hỏi.
            - Nên chọn các thực thể cấp cao hơn nếu có.
            Kết quả:
            Trả về kết quả là các class dưới dạng JSON như sau:
            {
                "Tên thực thể": [danh sách thực thể]
            }
            Ví dụ:
            Câu hỏi: "Hiệp ước Pháp - Hoa ký ngày 28-2-1946 có nội dung gì và tình hình sau đó đã đặt Việt Nam Dân chủ Cộng hòa trước lựa chọn nào?"
            Đáp án:
            {
                "Tên thực thể": ["Hiệp_ước_Pháp_-_Hoa"]
            }

            Câu hỏi: "Sau Cách mạng tháng Tám, chính phủ Việt Nam Dân chủ Cộng hòa đã thực hiện những biện pháp gì để khôi phục kinh tế và giải quyết nạn đói?"
            Đáp án:
            {
                "Tên thực thể": ["Khôi_phục_kinh_tế_111"]
            }
            Câu hỏi: "Chính phủ Việt Nam Dân chủ Cộng hòa đã có những biện pháp gì để đối phó với khó khăn về chính trị, kinh tế và ngoại giao trong năm 1945–1946"
            Đáp án:
            {
                "Tên thực thể": ["Khôi_phục_kinh_tế____","Tiếp_xúc_Việt-Pháp_1945", "Hiệp_ước_Pháp_-_Hoa"]
            }
            Nếu câu hỏi không có thông tin liên quan, trả về:
            {
                "Trong": []
            }
            """
        },
        {
            "role": "user",
            "content": f"CÁC THỰC THỂ VÀ CÁC QUAN HỆ TƯƠNG ỨNG:\n{json.dumps(relation, indent=4, ensure_ascii=False)}"
        },
        {
            "role": "user",
            "content": f"THÔNG TIN NGỮ CẢNH:\n{chat_history}"
        },
        {
            "role": "user",
            "content": f"CÂU HỎI:\n{question}"
        }
    ]

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        temperature=0,
        messages=messages
    )

    return response.choices[0].message.content


# def query_all(name_ontology, query_all_class_info, value):
#     prefix = f'''
#         PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
#         PREFIX owl: <http://www.w3.org/2002/07/owl#>
#         PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
#         PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
#         PREFIX {name_ontology}: <http://www.semanticweb.org/MINDMAP#>
#     '''
#     class_name = str(value).split('\\')[-1]
#     class_name = class_name.replace(f"{name_ontology}.", "")

#     # Truy vấn tất cả thông tin của class (predicate và giá trị)
#     query1 = f'''
#         SELECT ?summary
#         WHERE {{
#           {name_ontology}:{class_name} {name_ontology}:summary ?summary .
#         }}
#     '''
#     query_all_class_info.append(prefix + query1)


# def create_query(onto, name_ontology, json_data):
#     """
#     Tổng quát hóa hàm tạo query từ ontology dựa trên json_data.

#     Args:
#         onto: Ontology đang làm viec
#         name_ontology: Tên ontology đang làm việc
#         json_data: Dữ liệu JSON chứa các key và list các entity cần truy vấn

#     Returns:
#         list: Tất cả thông tin truy vấn được
#     """
#     query_all_class_info = []

#     for key, values in json_data.items():
#         has_class_parent = False
#         set_class_parent = set()
#         if key == "Trong":
#             continue  # Bỏ qua nếu key là 'Trong'

#         for value in values:
#             # Lấy thực thể từ ontology
#             entity = onto.search_one(iri="*" + value)
#             print("sau hàm search: ", entity)
#             if entity is None:
#                 print(f"[!] Không tìm thấy '{value}' trong ontology.")
#                 continue

#             # Nếu là class, xử lý bình thường
#             if isinstance(entity, ThingClass):
#                 children = onto.get_children_of(entity)
#                 query_all(name_ontology, query_all_class_info, entity)
#                 for child in children:
#                     query_all(name_ontology, query_all_class_info, child)
#             # Nếu là individual
#             else:
#                 class_parent = get_direct_class_of_individual(onto, value)
#                 set_class_parent.add(class_parent)
#                 has_class_parent = True
#         if has_class_parent:
#             for class_parent in set_class_parent:
#                 query_all(name_ontology, query_all_class_info, class_parent)

#     return query_all_class_info




# def find_question_info(name_ontology, list_query):
#     """
#     Chạy danh sách SPARQL query và trích xuất kết quả ra dạng text dễ đọc.

#     Args:
#         name_ontology: Tên ontology (dùng để bỏ prefix khi cần)
#         list_query: List query SPARQL cần thực thi

#     Returns:
#         list: Các kết quả đã tiền xử lý (list of list)
#     """
#     results = []

#     for query in list_query:
#         try:
#             query_result = list(default_world.sparql_query(query))
#         except Exception as e:
#             print(f"[!] Lỗi khi thực thi query: {e}")
#             continue

#         for record in query_result:
#             information = []
#             for val in record:
#                 processed_text = ""

#                 # Nếu có label thì ưu tiên lấy label
#                 if hasattr(val, "label") and val.label:
#                     processed_text = str(val.label[0])
#                 else:
#                     # Nếu không có label, thì xử lý text bình thường
#                     processed_text = str(val)
#                     if processed_text.startswith(f"{name_ontology}."):
#                         processed_text = processed_text.replace(f"{name_ontology}.", "")

#                     # Xử lý đặc biệt nếu cần (ví dụ trường hợp '9' bạn từng gặp)
#                     if processed_text == '9':
#                         processed_text = 'Là con của'

#                 information.append(processed_text)

#             results.append(information)

#     return results
def get_class_summary_annotation(ontology: Ontology, class_object) -> str | None:
    """
    Lấy giá trị của annotation "summary" cho một class cụ thể trong ontology.

    Args:
        ontology: Đối tượng ontology đã được load (ví dụ: onto).
        class_object: Object class trong ontology.

    Returns:
        Giá trị của annotation "summary" dưới dạng string,
        hoặc None nếu class không tồn tại, annotation "summary" không tồn tại,
        hoặc "summary" không phải là một AnnotationProperty hợp lệ.
    """
    if hasattr(class_object, "summary"):
        annotation_value = getattr(class_object, "summary")
        return annotation_value[0]
    return None

def find_question_info(onto, model_embedding, question, json_data):
    """
    Tổng quát hóa hàm tạo query từ ontology dựa trên json_data.

    Args:
        onto: Ontology đang làm viec
        name_ontology: Tên ontology đang làm việc
        json_data: Dữ liệu JSON chứa các key và list các entity cần truy vấn

    Returns:
        list: Tất cả thông tin truy vấn được
    """
    question_info = []
    key = list(json_data.keys())[0]
    values = json_data[key]
    # for key, values in json_data.items():
    if key == "Trong":
        return []  # Bỏ qua nếu key là 'Trong'

    for value in values:
        # Lấy thực thể từ ontology
        entity = onto.search_one(iri="*" + value)
        print("sau hàm search: ", entity)
        if entity is None:
            print(f"[!] Không tìm thấy '{value}' trong ontology.")
            continue

        # Nếu là class, xử lý bình thường
        if isinstance(entity, ThingClass):
            information = get_class_summary_annotation(onto, entity)
            if information is not None:
                question_info.append(information)

            children = onto.get_children_of(entity)
            for child in children:
                child_information = get_class_summary_annotation(onto, child)
                if child_information is not None:
                    question_info.append(child_information)

            string_names = [str(child_name).split('.')[-1] for child_name in children]
            string_names = [ name.replace('_',' ') for name in string_names]
            sorted_children = find_similar_info_from_raw_informations(model_embedding, question, string_names, k = 5)
            print("sorted_children: ", sorted_children)
            for name_child in sorted_children:
                name = name_child.replace(' ','_')
                child = onto.search_one(iri="*" + name)
                print("child tìm đươc: ",child)
                if child is None:
                    continue
                child_information = get_class_summary_annotation(onto, child)
                if child_information is not None:
                    question_info.append(child_information)
    return question_info
def generate_response(client ,question_info, question, history ):
  system_prompt  = f'''
            Bạn là một agent hữu ích giúp trả lời câu hỏi của người dùng dựa trên thông tin được cung cấp.
            Đồng thời dựa trên các thông tin này để cung cấp thêm thông tin gợi mở cho người đọc.
            Có thể trả về text dưới dạng mark down để tách biệt giữa thông tin trả lời và thông tin thêm.
            Dựa vào lịch sử cuộc trò chuyện để hiểu rõ hơn ngữ cảnh cuộc trò chuyện.
            THÔNG TIN:

            {question_info}

            LỊCH SỬ CUỘC TRÒ CHUYỆN:

            {history}

            Nếu không có câu trả lời, hãy nói: Tôi không biết, tôi chưa có kiến thức để trả lời câu hỏi này.
  '''
  response = client.chat.completions.create(
      model='gpt-4o-mini',
      temperature=0,
      messages=[
          {
              "role": "system",
              "content": system_prompt
          },
          {
              "role": "user",
              "content": question
          }
          ]
      )
  return response.choices[0].message.content

def get_embedding( model_embedding, text):
    # return model.encode(text)
    vector_embedding = model_embedding.encode( text, show_progress_bar=True)
    # The response data will be a list of embedding objects, each with a 'embedding' attribute
    return vector_embedding

def find_similar_info_from_raw_informations(model_embedding, question, result_from_ontology, k = 5):
    if len(result_from_ontology) <= k:
        return result_from_ontology

    embeddings_list = get_embedding(model_embedding, result_from_ontology)
    embeddings = np.array(embeddings_list, dtype=np.float32)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    similar_info = []

    # Get embedding for the question (which is a single string)
    question_embedding = get_embedding(model_embedding, [question])[0] # Get the single embedding from the list
    query_embedding = np.array(question_embedding, dtype=np.float32).reshape(1, -1) # Reshape for FAISS search

    distances, indices = index.search(query_embedding, k)

    # Retrieve the original raw information strings based on indices
    for idx in indices[0]:
        similar_info.append(result_from_ontology[idx])

    return similar_info
