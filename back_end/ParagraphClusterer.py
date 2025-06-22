
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import normalize
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import numpy as np

class ParagraphClusterer:
    """
    Một lớp để phân cụm các đoạn văn sử dụng S-BERT embeddings và K-Means.
    Cung cấp các chức năng để nhúng văn bản, phân cụm, lấy thông tin cụm
    và trực quan hóa kết quả phân cụm bằng PCA.
    """

    def __init__(self, model_embedding):
        """
        Khởi tạo ParagraphClusterer với một mô hình S-BERT.

        Args:
            model_name (str): Tên của mô hình S-BERT để sử dụng.
                              (Ví dụ: 'paraphrase-multilingual-MiniLM-L12-v2')
        """
        self.model = model_embedding
        self.paragraphs = []
        self.keywords = []
        self.paragraph_embeddings = None
        self.normalized_embeddings = None
        self.cluster_labels = None
        self.kmeans_model = None
        self.num_clusters = 0

    def embed_paragraphs(self, paragraphs: list, keywords: list):
        """
        Nhúng (embed) danh sách các đoạn văn thành vector số sử dụng S-BERT.

        Args:
            paragraphs (list): Một list các chuỗi (đoạn văn).
        """
        if not paragraphs:
            print("Danh sách đoạn văn rỗng. Không thể nhúng.")
            self.paragraphs = []
            self.keywords = []
            self.paragraph_embeddings = None
            self.normalized_embeddings = None
            return

        self.paragraphs = paragraphs
        self.keywords = keywords
        print("Đang nhúng các đoạn văn thành vector...")
        self.paragraph_embeddings = self.model.encode(paragraphs, show_progress_bar=True)
        # Chuẩn hóa vector ngay sau khi nhúng để sử dụng cho K-Means với cosine affinity
        self.normalized_embeddings = normalize(self.paragraph_embeddings, axis=1)
        print("Hoàn tất nhúng và chuẩn hóa vector.")

    def perform_kmeans_clustering(self, num_clusters: int, random_state: int = 42, n_init='auto', max_iter: int = 300):
        """
        Thực hiện phân cụm K-Means trên các vector đã nhúng.

        Args:
            num_clusters (int): Số lượng cụm mong muốn.
            random_state (int): Hạt giống cho khả năng tái tạo của K-Means.
            n_init (int or 'auto'): Số lần chạy K-Means với các hạt giống centroid khác nhau.
            max_iter (int): Số lần lặp tối đa của thuật toán K-Means.

        Returns:
            bool: True nếu phân cụm thành công, False nếu không.
        """
        if self.normalized_embeddings is None or not self.paragraphs:
            print("Chưa có vector đoạn văn nào được nhúng. Vui lòng gọi `embed_paragraphs` trước.")
            return False

        if num_clusters <= 0:
            print("Số lượng cụm phải lớn hơn 0.")
            return False

        if len(self.normalized_embeddings) < num_clusters:
            print(f"Số lượng đoạn văn ({len(self.normalized_embeddings)}) ít hơn số cụm mong muốn ({num_clusters})."
                  " Không thể tạo đủ cụm. Mỗi đoạn văn sẽ là một cụm riêng.")
            # Xử lý trường hợp này bằng cách gán mỗi đoạn văn vào một cụm riêng
            self.cluster_labels = np.arange(len(self.paragraphs))
            self.num_clusters = len(self.paragraphs)
            return True


        self.num_clusters = num_clusters
        print(f"Đang chạy MiniBatchKMeans với {self.num_clusters} cụm...")
        self.kmeans_model = MiniBatchKMeans(
            n_clusters=self.num_clusters,
            random_state=random_state,
            n_init=n_init,
            max_iter=max_iter
        )
        self.kmeans_model.fit(self.normalized_embeddings)
        self.cluster_labels = self.kmeans_model.labels_
        print("Hoàn tất phân cụm K-Means.")
        return True

    # --- Hàm tìm đoạn văn đại diện dưới dạng staticmethod ---
    @staticmethod
    def find_representative_paragraph(
        paragraph_indices_in_cluster: list,
        normalized_embeddings: np.ndarray,
        cluster_center_embedding: np.ndarray
    ) -> str:
        """
        Tìm đoạn văn gần nghĩa nhất với tâm cụm từ danh sách các đoạn văn trong cụm.
        Đây là một phương thức tĩnh vì nó không cần truy cập thuộc tính của đối tượng (self).
        """
        if not paragraph_indices_in_cluster:
            return "Không có đoạn văn trong cụm này."

        cluster_embeddings = normalized_embeddings[paragraph_indices_in_cluster]
        current_cluster_center_reshaped = cluster_center_embedding.reshape(1, -1)

        similarities = cosine_similarity(cluster_embeddings, current_cluster_center_reshaped).flatten()

        most_representative_index_in_cluster = np.argmax(similarities)
        original_paragraph_index = paragraph_indices_in_cluster[most_representative_index_in_cluster]

        return original_paragraph_index

    def get_cluster_info(self):
        """
        Lấy thông tin chi tiết về từng cụm đã được phân loại, bao gồm đoạn văn
        gần nghĩa nhất với tâm cụm làm đại diện.
        """
        if self.cluster_labels is None or not self.paragraphs or self.kmeans_model is None:
            print("Chưa có thông tin cụm. Vui lòng chạy `embed_paragraphs` và `perform_kmeans_clustering` trước.")
            return []

        clustered_data = [[] for _ in range(self.num_clusters)]
        for i, label in enumerate(self.cluster_labels):
            clustered_data[label].append(i)

        results = []
        cluster_centers = self.kmeans_model.cluster_centers_

        for cluster_id in range(self.num_clusters):
            paragraph_indices_in_cluster = clustered_data[cluster_id]
            current_cluster_center_embedding = cluster_centers[cluster_id]

            # Gọi staticmethod
            representative_paragraph_index = ParagraphClusterer.find_representative_paragraph(
                paragraph_indices_in_cluster,
                self.normalized_embeddings,
                current_cluster_center_embedding
            )

            results.append({
                "ID_of_cluster": cluster_id,
                "index_from_list_paragraph": paragraph_indices_in_cluster,
                "represent": self.paragraphs[representative_paragraph_index],
                "keyword": self.keywords[representative_paragraph_index]
            })
        return results

    def calculate_average_cosine_similarity(self):
        """
        Tính toán độ tương đồng cosine trung bình của mỗi cụm.

        Returns:
            dict: Dictionary chứa độ tương đồng cosine trung bình cho mỗi cụm.
                  Trả về dictionary rỗng nếu chưa phân cụm.
        """
        if self.cluster_labels is None or self.kmeans_model is None:
            print("Chưa có thông tin cụm để tính độ tương đồng. Vui lòng chạy `perform_kmeans_clustering` trước.")
            return {}

        avg_cosine_similarities_per_cluster = {}
        cluster_centers = self.kmeans_model.cluster_centers_ # Tâm cụm đã được chuẩn hóa

        for cluster_id in range(self.num_clusters):
            paragraph_indices_in_cluster = np.where(self.cluster_labels == cluster_id)[0]

            cluster_avg_similarity = 0.0 # Mặc định cho cụm rỗng

            if paragraph_indices_in_cluster.size > 0:
                cluster_embeddings = self.normalized_embeddings[paragraph_indices_in_cluster]

                if len(cluster_embeddings) > 1:
                    # Tính độ tương đồng giữa mỗi điểm và tâm cụm của nó
                    similarities = cosine_similarity(cluster_embeddings, cluster_centers[cluster_id].reshape(1, -1))
                    cluster_avg_similarity = np.mean(similarities)
                elif len(cluster_embeddings) == 1:
                    cluster_avg_similarity = 1.0 # Cụm chỉ có một phần tử có độ tương đồng là 1.0 với chính nó

            avg_cosine_similarities_per_cluster[f"Cụm {cluster_id}"] = cluster_avg_similarity
        return avg_cosine_similarities_per_cluster

    def plot_clusters_2d(self):
        """
        Trực quan hóa các cụm bằng cách giảm chiều dữ liệu về 2D bằng PCA
        và vẽ biểu đồ.
        """
        if self.normalized_embeddings is None or self.cluster_labels is None:
            print("Chưa có vector nhúng hoặc kết quả phân cụm để vẽ biểu đồ.")
            print("Vui lòng chạy `embed_paragraphs` và `perform_kmeans_clustering` trước.")
            return

        # Kiểm tra số lượng mẫu và số chiều
        if self.normalized_embeddings.shape[0] < 2:
            print("Không đủ điểm dữ liệu để thực hiện PCA và vẽ biểu đồ 2D.")
            return
        if self.normalized_embeddings.shape[1] < 2:
            print("Số chiều dữ liệu gốc quá thấp để giảm về 2D bằng PCA. Không thể vẽ biểu đồ 2D.")
            print("Cân nhắc vẽ biểu đồ 1D nếu phù hợp.")
            return

        print("Đang giảm chiều dữ liệu bằng PCA để trực quan hóa...")
        pca = PCA(n_components=2, random_state=42)
        reduced_embeddings = pca.fit_transform(self.normalized_embeddings)
        print("Hoàn tất giảm chiều dữ liệu.")

        plt.figure(figsize=(10, 8))
        colors = plt.cm.get_cmap('tab10', self.num_clusters)

        for i in range(self.num_clusters):
            cluster_points = reduced_embeddings[self.cluster_labels == i]
            plt.scatter(cluster_points[:, 0], cluster_points[:, 1],
                        s=50, color=colors(i), label=f'Cụm {i}', alpha=0.7)

        # Vẽ tâm cụm (sau khi giảm chiều)
        reduced_cluster_centers = pca.transform(self.kmeans_model.cluster_centers_)
        plt.scatter(reduced_cluster_centers[:, 0], reduced_cluster_centers[:, 1],
                    s=200, marker='X', color='black', label='Tâm cụm', edgecolor='white', linewidth=1.5)

        plt.title(f'Phân cụm các đoạn văn bằng K-Means ({self.num_clusters} cụm, PCA 2D)')
        plt.xlabel('Thành phần chính 1 (PCA 1)')
        plt.ylabel('Thành phần chính 2 (PCA 2)')
        plt.legend()
        plt.grid(True)
        plt.show()

    def find_optimal_clusters_elbow(self, k_range: range, random_state: int = 42, n_init='auto', max_iter: int = 300):
        """
        Tìm số cụm tối ưu bằng phương pháp Elbow (WCSS - Inertia)
        sử dụng MiniBatchKMeans.

        Args:
            k_range (range): Một range object xác định các giá trị k để kiểm tra (ví dụ: range(1, 11)).
            random_state (int): Hạt giống cho khả năng tái tạo của K-Means.
            n_init (int or 'auto'): Số lần chạy K-Means với các hạt giống centroid khác nhau.
            max_iter (int): Số lần lặp tối đa của thuật toán K-Means.

        Returns:
            list: Một list các giá trị WCSS (inertia) tương ứng với mỗi k.
        """
        if self.normalized_embeddings is None:
            print("Chưa có vector đoạn văn nào được nhúng. Vui lòng gọi `embed_paragraphs` trước.")
            return []

        if len(self.normalized_embeddings) < k_range.stop - 1:
            print(f"Số lượng đoạn văn ({len(self.normalized_embeddings)}) ít hơn số cụm tối đa ({k_range.stop -1})."
                  " Giới hạn phạm vi k để kiểm tra.")
            k_range = range(k_range.start, min(k_range.stop, len(self.normalized_embeddings) + 1))
            if k_range.stop <= k_range.start:
                print("Phạm vi k không hợp lệ sau khi điều chỉnh.")
                return []


        inertias = []
        print(f"Đang chạy MiniBatchKMeans để tìm k tối ưu qua phương pháp Elbow (kiểm tra k từ {k_range.start} đến {k_range.stop - 1})...")
        for k in k_range:
            if k == 0: continue # Bỏ qua k=0 vì không hợp lệ
            if k > len(self.normalized_embeddings): # Không thể có số cụm nhiều hơn số điểm
                break

            mb_kmeans = MiniBatchKMeans(
                n_clusters=k,
                random_state=random_state,
                n_init=n_init,
                max_iter=max_iter,
                batch_size=256 # Kích thước lô xử lý, có thể điều chỉnh
            )
            mb_kmeans.fit(self.normalized_embeddings)
            inertias.append(mb_kmeans.inertia_)
            print(f"  Đã tính WCSS cho k={k}: {mb_kmeans.inertia_:.2f}")

        # # Vẽ biểu đồ Elbow
        # plt.figure(figsize=(10, 6))
        # plt.plot(list(k_range)[:len(inertias)], inertias, marker='o', linestyle='-')
        # plt.title('Phương pháp Elbow để tìm số cụm tối ưu (WCSS vs. Số cụm K)')
        # plt.xlabel('Số cụm (K)')
        # plt.ylabel('Tổng bình phương khoảng cách trong cụm (WCSS/Inertia)')
        # plt.xticks(list(k_range)[:len(inertias)]) # Đảm bảo các nhãn x đúng với k
        # plt.grid(True)
        # plt.show()

        return inertias

