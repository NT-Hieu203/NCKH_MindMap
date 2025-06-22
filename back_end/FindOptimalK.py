import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from sklearn.metrics.pairwise import cosine_similarity

def find_optimal_k_elbow(k_range, inertias, method='knee', plot=True):
    """
    Tìm k tối ưu từ kết quả elbow method

    Parameters:
    -----------
    k_range : range hoặc list
        Phạm vi các giá trị k đã test
    inertias : list
        Danh sách các giá trị WCSS/inertia tương ứng với mỗi k
    method : str
        Phương pháp chọn k ('knee', 'elbow_distance', 'derivative')
    plot : bool
        Có vẽ biểu đồ hay không

    Returns:
    --------
    optimal_k : int
        Giá trị k tối ưu được chọn
    """

    k_values = list(k_range)


    if len(k_values) != len(inertias):
        print(f"Warning: k_range có {len(k_values)} phần tử, inertias có {len(inertias)} phần tử, tự động lấy số nhỏ hơn")

        # Tự động sửa lỗi bằng cách lấy số phần tử nhỏ hơn
        min_len = min(len(k_values), len(inertias))
        k_values = k_values[:min_len]
        inertias = inertias[:min_len]

    if len(k_values) == 0 or len(inertias) == 0:
        raise ValueError("Không có dữ liệu để xử lý")

    if method == 'knee':
        # Phương pháp Knee Locator - tìm điểm cong lớn nhất
        optimal_k = _find_knee_point(k_values, inertias)

    elif method == 'elbow_distance':
        # Phương pháp khoảng cách từ điểm đến đường thẳng nối 2 đầu
        optimal_k = _find_elbow_distance(k_values, inertias)

    elif method == 'derivative':
        # Phương pháp đạo hàm - tìm điểm thay đổi độ dốc lớn nhất
        optimal_k = _find_derivative_method(k_values, inertias)

    else:
        raise ValueError("Method phải là 'knee', 'elbow_distance', hoặc 'derivative'")

    if plot:
        _plot_elbow_analysis(k_values, inertias, optimal_k, method)

    return optimal_k

def _find_knee_point(k_values, inertias):
    """Tìm knee point bằng cách tính độ cong"""
    # Chuẩn hóa dữ liệu về [0,1]
    k_norm = np.array(k_values, dtype=float)
    k_norm = (k_norm - k_norm.min()) / (k_norm.max() - k_norm.min())

    inertias_norm = np.array(inertias, dtype=float)
    inertias_norm = (inertias_norm - inertias_norm.min()) / (inertias_norm.max() - inertias_norm.min())

    # Tính khoảng cách từ mỗi điểm đến đường thẳng nối 2 đầu
    distances = []
    for i in range(len(k_norm)):
        # Điểm hiện tại
        point = np.array([k_norm[i], inertias_norm[i]])

        # Đường thẳng từ điểm đầu đến điểm cuối
        line_start = np.array([k_norm[0], inertias_norm[0]])
        line_end = np.array([k_norm[-1], inertias_norm[-1]])

        # Tính khoảng cách từ điểm đến đường thẳng
        distance = np.abs(np.cross(line_end - line_start, line_start - point)) / np.linalg.norm(line_end - line_start)
        distances.append(distance)

    # Tìm điểm có khoảng cách lớn nhất
    optimal_idx = np.argmax(distances)
    return k_values[optimal_idx]

def _find_elbow_distance(k_values, inertias):
    """Tìm elbow bằng khoảng cách perpendicular"""
    # Tương tự như knee point nhưng dùng công thức khác
    points = np.array(list(zip(k_values, inertias)))

    # Đường thẳng từ điểm đầu đến điểm cuối
    line_vec = points[-1] - points[0]
    line_vec_norm = line_vec / np.sqrt(np.sum(line_vec**2))

    # Tính khoảng cách vuông góc
    distances = []
    for point in points:
        vec_to_point = point - points[0]
        scalar_proj = np.dot(vec_to_point, line_vec_norm)
        proj_point = points[0] + scalar_proj * line_vec_norm
        distance = np.sqrt(np.sum((point - proj_point)**2))
        distances.append(distance)

    optimal_idx = np.argmax(distances)
    return k_values[optimal_idx]

def _find_derivative_method(k_values, inertias):
    """Tìm k tối ưu bằng phương pháp đạo hàm"""
    # Tính đạo hàm bậc 1
    first_derivatives = np.diff(inertias)

    # Tính đạo hàm bậc 2 (độ thay đổi của đạo hàm bậc 1)
    second_derivatives = np.diff(first_derivatives)

    # Tìm điểm có độ thay đổi lớn nhất (đạo hàm bậc 2 lớn nhất)
    if len(second_derivatives) > 0:
        optimal_idx = np.argmax(np.abs(second_derivatives)) + 1  # +1 vì diff làm giảm 1 phần tử
        return k_values[optimal_idx]
    else:
        # Fallback: chọn điểm giữa
        return k_values[len(k_values)//2]

def _plot_elbow_analysis(k_values, inertias, optimal_k, method):
    """Vẽ biểu đồ elbow với điểm tối ưu được đánh dấu"""
    plt.figure(figsize=(10, 6))

    # Vẽ đường elbow
    plt.plot(k_values, inertias, 'bo-', linewidth=2, markersize=8, label='WCSS')

    # Đánh dấu điểm tối ưu
    optimal_idx = k_values.index(optimal_k)
    plt.plot(optimal_k, inertias[optimal_idx], 'ro', markersize=12,
             label=f'K tối ưu = {optimal_k}')

    # Vẽ đường thẳng từ điểm đầu đến điểm cuối (để thấy rõ elbow)
    plt.plot([k_values[0], k_values[-1]], [inertias[0], inertias[-1]],
             'r--', alpha=0.5, label='Đường thẳng tham chiếu')

    plt.xlabel('Số cụm (K)')
    plt.ylabel('WCSS (Within-Cluster Sum of Squares)')
    plt.title(f'Elbow Method - Phương pháp: {method}')
    plt.grid(True, alpha=0.3)
    plt.legend()

    # Thêm annotation
    plt.annotate(f'K = {optimal_k}',
                xy=(optimal_k, inertias[optimal_idx]),
                xytext=(optimal_k + 0.5, inertias[optimal_idx] + max(inertias) * 0.1),
                arrowprops=dict(arrowstyle='->', color='red'),
                fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.show()

# Hàm wrapper để sử dụng dễ dàng hơn
def auto_select_optimal_k(k_range, inertias, show_comparison=True):
    """
    Tự động chọn k tối ưu bằng cách thử 3 phương pháp và chọn kết quả phổ biến nhất

    Parameters:
    -----------
    k_range : range hoặc list
        Phạm vi các giá trị k đã test
    inertias : list
        Danh sách các giá trị WCSS/inertia
    show_comparison : bool
        Có hiển thị so sánh các phương pháp hay không

    Returns:
    --------
    optimal_k : int
        Giá trị k tối ưu được chọn
    """

    methods = ['knee', 'elbow_distance', 'derivative']
    results = {}

    for method in methods:
        try:
            k_opt = find_optimal_k_elbow(k_range, inertias, method=method, plot=False)
            results[method] = k_opt
        except:
            results[method] = None

    if show_comparison:
        print("--- So sánh các phương pháp chọn k tối ưu ---")
        for method, k_opt in results.items():
            if k_opt is not None:
                print(f"{method.capitalize():15}: K = {k_opt}")
            else:
                print(f"{method.capitalize():15}: Lỗi")

    # Chọn k xuất hiện nhiều nhất, nếu không có thì chọn knee method
    valid_results = [k for k in results.values() if k is not None]

    if not valid_results:
        return list(k_range)[len(list(k_range))//2]  # Fallback: chọn giữa

    # Tìm k xuất hiện nhiều nhất
    from collections import Counter
    k_counts = Counter(valid_results)
    most_common_k = k_counts.most_common(1)[0][0]

    if show_comparison:
        print(f"\n==> K tối ưu được chọn: {most_common_k}")

    return most_common_k

def get_safe_k_range(n_samples, min_k=2, max_k=None):
    """
    Tạo k_range an toàn dựa trên số lượng samples, từ 2 -> n_samples-2

    Parameters:
    -----------
    n_samples : int
        Số lượng samples (đoạn văn)
    min_k : int
        K tối thiểu (mặc định 2)
    max_k : int
        K tối đa (mặc định None - sẽ tự động tính)

    Returns:
    --------
    safe_range : range
        Range k an toàn
    """
    if max_k is None:
        # K tối đa = min(n_samples, n_samples//2 + 3) để tránh overfitting
        max_k = min(n_samples, max(n_samples//2 + 3, min_k + 2))

    max_k = min(max_k, n_samples)  # Đảm bảo k <= n_samples

    print(f"Với {n_samples} đoạn văn:")
    print(f"- K range an toàn: {min_k} đến {max_k}")
    print(f"- Gợi ý: Sử dụng range({min_k}, {max_k + 1})")

    return range(min_k, max_k + 1 )

def should_merge_to_single_cluster(list_paragraphs, embeddings=None, clusterer=None, strategy='adaptive'):
    """
    Quyết định có nên gom tất cả về 1 cụm cuối cùng hay không

    Args:
        list_paragraphs: Danh sách các đoạn văn hiện tại
        embeddings: Vector embeddings của các đoạn văn
        clusterer: Đối tượng ParagraphClusterer
        strategy: Chiến lược quyết định ('adaptive', 'threshold', 'fixed', 'similarity')

    Returns:
        bool: True nếu nên gom về 1 cụm
    """
    n_paragraphs = len(list_paragraphs)

    if strategy == 'fixed':
        # Chiến lược cố định: Nếu còn <= N đoạn thì gom về 1
        threshold = 3  # Có thể điều chỉnh
        return n_paragraphs <= threshold

    elif strategy == 'threshold':
        # Chiến lược ngưỡng động: Dựa trên tỷ lệ giảm
        if n_paragraphs <= 2:
            return True
        elif n_paragraphs <= 5:
            return True  # Nếu còn ít, gom luôn
        else:
            return False

    elif strategy == 'similarity':
        # Chiến lược độ tương đồng: Nếu các đoạn văn đủ tương đồng thì gom
        if embeddings is not None and n_paragraphs > 1:
            # Tính độ tương đồng trung bình giữa tất cả các cặp
            similarity_matrix = cosine_similarity(embeddings)
            # Lấy tam giác trên (không tính đường chéo)
            upper_triangle = similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)]
            avg_similarity = np.mean(upper_triangle)

            print(f"  → Độ tương đồng trung bình: {avg_similarity:.4f}")

            # Nếu độ tương đồng cao (>0.7) hoặc còn ít đoạn (<=4) thì gom
            if avg_similarity > 0.7 or n_paragraphs <= 4:
                return True
            else:
                return False
        else:
            return n_paragraphs <= 3

    elif strategy == 'adaptive':
        # Chiến lược thích ứng: Kết hợp nhiều yếu tố

        # Yếu tố 1: Số lượng đoạn văn
        if n_paragraphs <= 2:
            print(f"  → Chỉ còn {n_paragraphs} đoạn - Gom về 1 cụm")
            return True

        # Yếu tố 2: Độ tương đồng cao
        if embeddings is not None and n_paragraphs > 2:
            similarity_matrix = cosine_similarity(embeddings)
            upper_triangle = similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)]
            avg_similarity = np.mean(upper_triangle)
            min_similarity = np.min(upper_triangle)

            print(f"  → Độ tương đồng TB: {avg_similarity:.4f}, Min: {min_similarity:.4f}")

            # Nếu độ tương đồng trung bình cao và tối thiểu không quá thấp
            if avg_similarity > 0.75 and min_similarity > 0.5:
                print(f"  → Độ tương đồng cao - Gom về 1 cụm")
                return True

            # Nếu còn ít đoạn và độ tương đồng khá
            if n_paragraphs <= 4 and avg_similarity > 0.6:
                print(f"  → Còn ít đoạn + độ tương đồng khá - Gom về 1 cụm")
                return True

        # Yếu tố 3: Giới hạn số vòng lặp (tránh vô hạn)
        if n_paragraphs <= 5:
            print(f"  → Còn {n_paragraphs} đoạn - Cân nhắc gom về 1 cụm")
            return True

        return False

    else:
        # Mặc định: chỉ gom khi còn 2 đoạn
        return n_paragraphs <= 2

def get_optimal_k_with_final_merge_logic(list_paragraphs, clusterer, strategy='adaptive'):
    """
    Lấy số cụm tối ưu với logic gom cụm cuối thông minh
    """
    n_paragraphs = len(list_paragraphs)

    print(f"Đang phân tích {n_paragraphs} đoạn văn...")

    # Kiểm tra xem có nên gom về 1 cụm không
    should_merge = should_merge_to_single_cluster(
        list_paragraphs,
        clusterer.embeddings if hasattr(clusterer, 'embeddings') else None,
        clusterer,
        strategy
    )

    if should_merge:
        print("  → Quyết định: Gom tất cả về 1 cụm cuối cùng")
        return 1

    # Nếu không gom về 1, thì dùng phương pháp elbow bình thường
    print("  → Quyết định: Sử dụng phương pháp elbow để tìm k tối ưu")

    # Đảm bảo k không quá lớn so với số đoạn văn

    k_test_range = get_safe_k_range(len(list_paragraphs), min_k=1, max_k=None)

    inertias = clusterer.find_optimal_clusters_elbow(k_test_range)

    if inertias:
        optimal_k = auto_select_optimal_k(k_test_range, inertias, show_comparison=True)
        return optimal_k
    else:
        return -1
# --- SỬ DỤNG ---
# Chọn 1 trong các chiến lược sau:
# 'adaptive'   - Thích ứng thông minh (khuyến nghị)
# 'similarity' - Dựa trên độ tương đồng
# 'threshold'  - Ngưỡng cố định
# 'fixed'      - Số lượng cố định