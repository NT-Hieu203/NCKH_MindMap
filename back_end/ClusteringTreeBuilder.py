import json
from datetime import datetime

class ClusteringTreeBuilder:
    def __init__(self):
        self.tree = []  # Danh sách các node trong cây
        self.current_index = 0  # Index hiện tại cho node mới
        self.round_mapping = {}  # Mapping giữa các vòng

    def add_initial_paragraphs(self, client, paragraphs, keywords):
        """
        Thêm các đoạn văn ban đầu vào cây (các node lá)
        """
        initial_indices = []

        for summarized_paragraph, keyword in zip(paragraphs, keywords ):
            node = {
                'index': self.current_index,
                'parent_index': -1,  # Node gốc không có parent
                'summarized_paragraph': summarized_paragraph,
                'keyword': keyword,
                'type': 'leaf_node',  # Loại: đoạn văn gốc
                'round': 0,  # Vòng 0 = dữ liệu ban đầu
                'cluster_id': None,  # Chưa thuộc cụm nào
                'children': []  # Danh sách các node con
            }

            self.tree.append(node)
            initial_indices.append(self.current_index)
            self.current_index += 1

        # Lưu mapping cho vòng 0
        self.round_mapping[0] = initial_indices

        print(f"✅ Đã thêm {len(paragraphs)} đoạn văn ban đầu vào cây")
        return initial_indices

    def add_cluster_round(self, cluster_info, round_number, input_indices):
        """
        Thêm một vòng phân cụm vào cây

        Args:
            cluster_info: Thông tin các cụm từ clusterer
            round_number: Số vòng hiện tại
            input_indices: Danh sách index của các node input cho vòng này
        """
        new_indices = []

        print(f"\n🔄 Đang xử lý vòng {round_number} với {len(cluster_info)} cụm...")

        # Xác định xem đây có phải là vòng cuối cùng dẫn đến một cụm duy nhất hay không
        is_final_single_cluster_round = (len(cluster_info) == 1)

        for cluster in cluster_info:
            # Gán type là 'root_node' nếu đây là cụm duy nhất của vòng cuối cùng
            node_type = 'internal_node'
            if is_final_single_cluster_round:
                node_type = 'root_node'

            summarized_paragraph = cluster['represent']
            keyword = cluster['keyword']
            cluster_node = {
                'index': self.current_index,
                'parent_index': -1,  # Sẽ được cập nhật sau
                'summarized_paragraph': summarized_paragraph,
                'keyword': keyword,
                'type': node_type, # Đặt type dựa trên điều kiện
                'round': round_number,
                'cluster_id': cluster['ID_of_cluster'],
                'children': [],
                'original_indices': []  # Lưu các index gốc mà cụm này đại diện
            }

            # Xác định các node con (node input thuộc cụm này)
            children_indices = []
            for input_idx_in_cluster_info in cluster['index_from_list_paragraph']:
                # Ánh xạ index từ danh sách clusterer sang index trong cây
                if input_idx_in_cluster_info < len(input_indices):
                    child_tree_index = input_indices[input_idx_in_cluster_info]
                    children_indices.append(child_tree_index)

                    # Cập nhật parent cho node con
                    child_node_in_tree = self.get_node_by_index(child_tree_index)
                    if child_node_in_tree:
                        child_node_in_tree['parent_index'] = self.current_index

            # Cập nhật thông tin children
            cluster_node['children'] = children_indices

            # Thu thập tất cả các index gốc mà cụm này đại diện
            original_indices_set = set()
            for child_idx in children_indices:
                child_node = self.get_node_by_index(child_idx)
                if child_node:
                    if child_node['type'] == 'leaf_node':
                        original_indices_set.add(child_idx)
                    else:
                        original_indices_set.update(child_node.get('original_indices', []))

            cluster_node['original_indices'] = sorted(list(original_indices_set))

            self.tree.append(cluster_node)
            new_indices.append(self.current_index)
            self.current_index += 1

        # Lưu mapping cho vòng này
        self.round_mapping[round_number] = new_indices

        print(f"✅ Đã thêm {len(cluster_info)} cụm đại diện cho vòng {round_number}")
        return new_indices

    def get_node_by_index(self, index):
        """Lấy node theo index"""
        for node in self.tree:
            if node['index'] == index:
                return node
        return None

    def get_tree_structure(self):
        """Trả về cấu trúc cây hoàn chỉnh"""
        return self.tree

    def get_root_nodes(self):
        """
        Lấy các node gốc (có type là 'root_node').
        Nếu không tìm thấy, sẽ trả về các node không có parent ở vòng cuối cùng (fallback).
        """
        # Ưu tiên tìm node có type là 'root_node'
        roots_by_type = [node for node in self.tree if node.get('type') == 'root_node']
        if roots_by_type:
            return roots_by_type

        # Fallback: Nếu không có node nào được đánh dấu rõ ràng là 'root_node'
        # (ví dụ: quá trình dừng sớm hoặc chưa gom về 1 cụm hoàn chỉnh)
        # thì tìm các node không có parent ở vòng cao nhất.
        if not self.round_mapping:
            return []

        max_round = max(self.round_mapping.keys())
        roots = []
        for node_index in self.round_mapping[max_round]:
            node = self.get_node_by_index(node_index)
            # Kiểm tra node['parent_index'] is None để đảm bảo nó là nút "trên cùng"
            # của nhánh đó. Nếu có nhiều hơn 1 nút ở top level, chúng sẽ được trả về.
            if node and node['parent_index'] is None:
                roots.append(node)
        return roots

    def print_tree_summary(self):
        """In tóm tắt cây"""
        print(f"\n{'='*60}")
        print("🌳 TÓM TẮT CÂY PHÂN CỤM")
        print(f"{'='*60}")
        print(f"Tổng số node: {len(self.tree)}")
        print(f"Số vòng phân cụm: {max(self.round_mapping.keys()) if self.round_mapping else 0}")

        # Thống kê theo vòng
        for round_num in sorted(self.round_mapping.keys()):
            indices = self.round_mapping[round_num]
            if round_num == 0:
                print(f"  Vòng {round_num} (Dữ liệu gốc): {len(indices)} đoạn văn")
            else:
                print(f"  Vòng {round_num}: {len(indices)} cụm đại diện")

        # Thống kê node gốc
        roots = self.get_root_nodes()
        print(f"Số node gốc cuối cùng: {len(roots)}")

        if len(roots) == 1:
            print("✅ Đã gom thành công về 1 cụm duy nhất!")

    def export_to_json(self, filename=None):
        """Xuất cây ra file JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"clustering_tree_{timestamp}.json"

        export_data = {
            'metadata': {
                'total_nodes': len(self.tree),
                'rounds': len(self.round_mapping),
                'created_at': datetime.now().isoformat(),
                'final_clusters': len(self.get_root_nodes())
            },
            'round_mapping': self.round_mapping,
            'tree': self.tree
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"📁 Đã xuất cây ra file: {filename}")
        return filename

    def visualize_tree_structure(self, max_content_length=50):
        """Hiển thị cấu trúc cây dạng text"""
        print(f"\n{'='*80}")
        print("🌳 CẤU TRÚC CÂY PHÂN CỤM")
        print(f"{'='*80}")

        # Hiển thị theo vòng từ cuối về đầu
        for round_num in sorted(self.round_mapping.keys(), reverse=True):
            indices = self.round_mapping[round_num]

            if round_num == 0:
                print(f"\n📄 VÒNG {round_num} - DỮ LIỆU GỐC ({len(indices)} đoạn):")
                for idx in indices[:5]:  # Chỉ hiển thị 5 đoạn đầu
                    node = self.get_node_by_index(idx)
                    if node:
                        content = node['summarized_paragraph'][:max_content_length]
                        if len(node['summarized_paragraph']) > max_content_length:
                            content += "..."
                        print(f"  📝 [{idx}] {content}")
                if len(indices) > 5:
                    print(f"      ... và {len(indices) - 5} đoạn khác")
            else:
                print(f"\n🔄 VÒNG {round_num} - CÁC CỤM ĐẠI DIỆN ({len(indices)} cụm):")
                for idx in indices:
                    node = self.get_node_by_index(idx)
                    if node:
                        content = node['summarized_paragraph'][:max_content_length]
                        if len(node['summarized_paragraph']) > max_content_length:
                            content += "..."

                        children_info = f"({len(node['children'])} con)" if node['children'] else ""
                        original_info = f"[{len(node.get('original_indices', []))} gốc]"

                        print(f"  🔸 [{idx}] Cụm {node['cluster_id']} {children_info} {original_info}")
                        print(f"      \"{content}\"")

                        # Hiển thị các con
                        if node['children'] and len(node['children']) <= 5:
                            for child_idx in node['children']:
                                child_node = self.get_node_by_index(child_idx)
                                if child_node:
                                    child_content = child_node['summarized_paragraph'][:30] + "..."
                                    print(f"        ↳ [{child_idx}] {child_content}")