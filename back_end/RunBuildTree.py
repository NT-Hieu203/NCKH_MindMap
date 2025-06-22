from ParagraphClusterer import *
from ClusteringTreeBuilder import *
from PDF_Processor import summary_paragraph, extract_key_word
import time
from FindOptimalK import get_optimal_k_with_final_merge_logic
def run_clustering_with_tree_building(client, model_embedding, list_node , clustering_strategy='adaptive'):
    """
    Chạy phân cụm và xây dựng cây đồng thời
    """
    # Khởi tạo các đối tượng
    clusterer = ParagraphClusterer(model_embedding)
    tree_builder = ClusteringTreeBuilder()

    # Dữ liệu ban đầu
    initial_paragraphs = [paragraph['full_text'] for paragraph in list_node]
    s_time = time.time()
    initial_summarized_paragraphs = []
    for full_paragraph in initial_paragraphs:
        summarized_paragraph = summary_paragraph(client, full_paragraph )
        initial_summarized_paragraphs.append(summarized_paragraph)

    list_paragraphs = initial_summarized_paragraphs.copy()
    list_keywords = [extract_key_word(client, paragraph) for paragraph in initial_paragraphs]
    e_time = time.time()
    print(f"Thời gian summarize và tách key word: {e_time - s_time}s")

    print(f"🚀 BẮT ĐẦU PHÂN CỤM VÀ XÂY DỰNG CÂY")
    print(f"Số đoạn văn ban đầu: {len(initial_paragraphs)}")

    # Thêm các đoạn văn ban đầu vào cây, các nút lá
    current_indices = tree_builder.add_initial_paragraphs(client, paragraphs = initial_summarized_paragraphs, keywords=list_keywords)

    round_count = 1

    while len(list_paragraphs) > 1:
        print(f"\n{'='*60}")
        print(f"--- VÒNG {round_count} | Số đoạn hiện tại: {len(list_paragraphs)} ---")
        print(f"{'='*60}")

        # Nhúng các đoạn văn thành vector
        clusterer.embed_paragraphs(list_paragraphs, list_keywords)

        # Lấy số cụm tối ưu
        optimal_k = get_optimal_k_with_final_merge_logic(
            list_paragraphs,
            clusterer,
            clustering_strategy
        )

        print(f"\n🎯 Số cụm được chọn: {optimal_k}")

        # Thực hiện phân cụm
        if clusterer.perform_kmeans_clustering(optimal_k):
            cluster_info = clusterer.get_cluster_info()

            # Thêm vào cây
            new_indices = tree_builder.add_cluster_round(
                cluster_info,
                round_count,
                current_indices
            )

            # Cập nhật cho vòng lặp tiếp theo
            previous_count = len(list_paragraphs)
            list_paragraphs = [cluster['represent'] for cluster in cluster_info]
            list_keywords = [cluster['keyword'] for cluster in cluster_info]

            current_indices = new_indices
            current_count = len(list_paragraphs)

            print(f"\n📉 Giảm từ {previous_count} xuống {current_count} đoạn")

            # Kiểm tra điều kiện dừng
            if current_count == 1:
                print(f"\n🎉 ĐẠT ĐƯỢC MỤC TIÊU: Gom thành 1 đoạn cuối cùng!")
                break

        else:
            print("\n❌ Phân cụm không thành công - Dừng quá trình")
            break

        round_count += 1

        # Bảo vệ tránh vòng lặp vô hạn
        if round_count > 20:
            print("\n⚠️ Đã chạy quá 20 vòng - Dừng để tránh vô hạn")
            break

    # # Hiển thị kết quả
    # tree_builder.print_tree_summary()
    # tree_builder.visualize_tree_structure()
    #
    # # Xuất file
    # # json_file = tree_builder.export_to_json()

    return {
        'tree': tree_builder.get_tree_structure(),
        'tree_builder': tree_builder
    }
