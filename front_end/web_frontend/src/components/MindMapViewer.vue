<template>
    <div class="mindmap-viewer-container">
        <div v-if="!processedTreeData || !processedTreeData.data || !processedTreeData.data.keyword" class="no-data-message">
            <p>Không có dữ liệu để tạo Mindmap. Vui lòng upload PDF.</p>
        </div>
        <div v-else class="mindmap-area" ref="mindmapArea">
            <svg ref="mindmapSvg"></svg>
            <div class="zoom-controls">
                <button @click="zoomIn" title="Phóng to">+</button>
                <button @click="zoomOut" title="Thu nhỏ">-</button>
                <button @click="resetZoom" title="Đặt lại hiển thị">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
                        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="2" y1="12" x2="22" y2="12"></line>
                        <line x1="12" y1="2" x2="12" y2="22"></line>
                    </svg>
                </button>
            </div>
            <div v-if="tooltip.visible" :style="tooltipStyle" class="mindmap-tooltip">
                {{ tooltip.content }}
            </div>
        </div>
    </div>
</template>

<script>
import * as d3 from 'd3';

export default {
    name: "MindMapViewer",
    props: {
        // Đổi tên prop từ rawData thành data
        data: {
            type: Array,
            default: () => []
        }
    },
    data() {
        return {
            svgWidth: 800,
            svgHeight: 600,
            svg: null, // D3 selection cho thẻ SVG
            g: null, // Nhóm chứa nội dung, phục vụ zoom/pan
            zoomBehavior: null,
            transform: d3.zoomIdentity,
            nodeColors: [
                "#4a90e2", "#f7941d", "#69b3a2", "#f06969", "#81b214",
                "#a566ff", "#e056fd", "#2ecc71"
            ],
            rootNodeColor: "#2c3e50",
            tooltip: {
                visible: false,
                content: '',
                x: 0,
                y: 0
            },
            // Cấu hình kích thước node và khoảng cách
            nodePadding: { horizontal: 25, vertical: 20 }, // Padding bên trong node
            minNodeWidth: 140, // Chiều rộng tối thiểu của node
            maxNodeWidth: 280, // Chiều rộng tối đa của node để xuống dòng
            nodeHeightPerLine: 22, // Chiều cao ước tính cho mỗi dòng text
            minNodeHeight: 50, // Chiều cao tối thiểu của node
            horizontalNodeSeparation: 350, // Khoảng cách ngang giữa các node mặc định
            verticalNodeSeparation: 120, // Khoảng cách dọc giữa các node mặc định
        };
    },
    computed: {
        processedTreeData() {
            // Sử dụng prop 'data' thay vì 'rawData'
            if (this.data.length === 0) {
                return null;
            }

            const dataMap = new Map(
                this.data.map(d => [d.index, { ...d, children: [] }])
            );

            let rootNode = null;
            this.data.forEach(item => {
                if (item.parent_index === -1) {
                    rootNode = dataMap.get(item.index);
                } else {
                    const parent = dataMap.get(item.parent_index);
                    if (parent) {
                        parent.children.push(dataMap.get(item.index));
                    }
                }
            });

            if (!rootNode) {
                console.warn("No root node found or data is malformed.");
                return null;
            }

            // Gán màu cho từng nhánh từ nút gốc
            let colorIndex = 0;
            rootNode.children.forEach(mainBranch => {
                const color = this.nodeColors[colorIndex % this.nodeColors.length];
                colorIndex++;
                const assignBranchColor = node => {
                    node.color = color;
                    if (node.children) {
                        node.children.forEach(child => assignBranchColor(child));
                    }
                };
                assignBranchColor(mainBranch);
            });
            rootNode.color = this.rootNodeColor;

            return d3.hierarchy(rootNode, d => d.children);
        },
        tooltipStyle() {
            return {
                top: `${this.tooltip.y}px`,
                left: `${this.tooltip.x}px`,
                transform: 'translate(-50%, -110%)', // Đảm bảo tooltip ở trên và căn giữa
                display: this.tooltip.visible ? 'block' : 'none',
            };
        }
    },
    watch: {
        // Lắng nghe sự thay đổi của prop 'data'
        data: {
            handler(newVal) {
                if (newVal && newVal.length > 0) {
                    this.$nextTick(() => {
                        this.updateSvgSize();
                        this.setupMindmap();
                    });
                } else {
                    this.cleanupMindmap();
                }
            },
            immediate: true,
            deep: true
        }
    },
    mounted() {
        this.updateSvgSize();
        window.addEventListener('resize', this.updateSvgSize);
    },
    beforeUnmount() {
        this.cleanupMindmap();
        window.removeEventListener('resize', this.updateSvgSize);
    },
    methods: {
        updateSvgSize() {
            if (this.$refs.mindmapArea && this.$refs.mindmapSvg) {
                const rect = this.$refs.mindmapArea.getBoundingClientRect();
                this.svgWidth = rect.width;
                this.svgHeight = rect.height;
                d3.select(this.$refs.mindmapSvg)
                    .attr("width", this.svgWidth)
                    .attr("height", this.svgHeight);
                if (this.processedTreeData) {
                    this.setupMindmap(); // Re-render mindmap to adjust layout for new size
                }
            }
        },
        setupMindmap() {
    if (this.svg) {
        this.svg.selectAll("*").remove();
    } else {
        this.svg = d3.select(this.$refs.mindmapSvg);
    }

    this.g = this.svg.append('g');

    this.zoomBehavior = d3.zoom()
        .scaleExtent([0.1, 4]) // Mở rộng giới hạn zoom
        .on("zoom", event => {
            this.transform = event.transform;
            this.g.attr("transform", this.transform);
        });
    this.svg.call(this.zoomBehavior);

    // --- Bước 1: Tiền xử lý text để tính toán kích thước node ---
    // Tạo một SVG tạm thời ẩn để đo kích thước text
    const tempSvg = d3.select("body").append("svg").style("position", "absolute").style("left", "-9999px");
    const tempText = tempSvg.append("text")
        .attr("class", "node-text")
        .style("font-weight", "bold") // In đậm chữ khi đo
        .style("font-family", "K2D, sans-serif"); // Áp dụng font K2D khi đo

    this.processedTreeData.each(d => {
        // Xác định kích thước font dựa trên loại node
        const fontSize = d.data.type === 'root_node' ? 20 : 18;
        tempText.style("font-size", `${fontSize}px`); // Áp dụng kích thước font khi đo

        const keyword = d.data.keyword || '';
        const words = keyword.split(/\s+/);
        let currentLine = '';
        let lineCount = 0;
        let maxWidth = 0;
        const wrappedLines = [];

        for (let i = 0; i < words.length; i++) {
            const testLine = currentLine + (words[i] ? (i > 0 ? " " : "") + words[i] : "");
            tempText.text(testLine);
            const currentTextWidth = tempText.node().getComputedTextLength();

            if (currentTextWidth > this.maxNodeWidth && currentLine !== '') {
                wrappedLines.push(currentLine);
                lineCount++;
                maxWidth = Math.max(maxWidth, tempText.text(currentLine).node().getComputedTextLength());
                currentLine = words[i];
            } else {
                currentLine = testLine;
            }
        }
        wrappedLines.push(currentLine);
        lineCount++;
        maxWidth = Math.max(maxWidth, tempText.text(currentLine).node().getComputedTextLength()); // Đo dòng cuối cùng

        d.data.wrappedKeyword = wrappedLines;
        d.data.nodeCalculatedWidth = Math.max(this.minNodeWidth, maxWidth + this.nodePadding.horizontal * 2);
        // Điều chỉnh nodeHeightPerLine dựa trên fontSize để tính toán chiều cao chính xác hơn
        d.data.nodeCalculatedHeight = Math.max(this.minNodeHeight, lineCount * (fontSize * 1.2) + this.nodePadding.vertical * 2); // Ước tính chiều cao dòng dựa trên font size
        // Lưu trữ fontSize đã dùng để render sau này
        d.data.currentFontSize = fontSize; 
    });

    tempSvg.remove(); // Xóa SVG tạm thời

    // --- Bước 2: Thiết lập Tree Layout ---
    const treeLayout = d3.tree()
        .nodeSize([this.verticalNodeSeparation, this.horizontalNodeSeparation]) // [height, width] cho mỗi node
        // Sử dụng separation để tùy chỉnh khoảng cách chi tiết hơn
        .separation((a, b) => {
            // Khoảng cách ngang: đảm bảo đủ chỗ cho cả hai node + padding
            const nodeWidthA = a.data.nodeCalculatedWidth || this.minNodeWidth;
            const nodeWidthB = b.data.nodeCalculatedWidth || this.minNodeWidth;

            // Khoảng cách dọc: đảm bảo đủ chỗ cho cả hai node + padding
            const nodeHeightA = a.data.nodeCalculatedHeight || this.minNodeHeight;
            const nodeHeightB = b.data.nodeCalculatedHeight || this.minNodeHeight;

            if (a.parent === b.parent) {
                return 1.5;
            } else {
                return 3; // Giá trị lớn hơn sẽ đẩy chúng xa hơn theo chiều ngang
            }
        });

    // Chạy layout để tính toán vị trí cuối cùng của các node
    const root = treeLayout(this.processedTreeData);

    // --- Bước 3: Render các đường nối ---
    this.g.selectAll('.link')
        .data(root.links())
        .enter()
        .append('path')
        .attr('class', 'link')
        .attr('fill', 'none')
        .attr('stroke', d => d.target.data.color || '#ccc')
        .attr('stroke-width', 2)
        .attr("d", d3.linkHorizontal()
            .x(d => d.y)
            .y(d => d.x)
        );

    // --- Bước 4: Render các nút ---
    const nodeEnter = this.g.selectAll('.node')
        .data(root.descendants())
        .enter()
        .append('g')
        .attr('class', d => `node node-${d.data.type}`)
        .attr('transform', d => `translate(${d.y}, ${d.x})`);

    // Thêm hình chữ nhật
    nodeEnter.append('rect')
        .attr('class', 'node-rect')
        .attr('rx', 8) // bo góc
        .attr('ry', 8) // bo góc
        .attr('width', d => d.data.nodeCalculatedWidth)
        .attr('height', d => d.data.nodeCalculatedHeight)
        .attr('x', d => -d.data.nodeCalculatedWidth / 2) // Căn giữa
        .attr('y', d => -d.data.nodeCalculatedHeight / 2) // Căn giữa
        .attr('fill', d => d.data.color || "#fff")
        .attr('stroke', '#999')
        .attr('stroke-width', 2);

    // Thêm text đã xuống dòng
    nodeEnter.selectAll('.node-text')
    .data(d => d.data.wrappedKeyword.map((line, i) => ({ line: line, parent: d, index: i })))
    .enter()
    .append('text')
    .attr('class', 'node-text')
    .attr('x', 0) // Căn giữa theo chiều ngang
    .attr('y', (d) => {
        const totalLines = d.parent.data.wrappedKeyword.length;
        const lineHeight = d.parent.data.currentFontSize * 1.2; 
        const startY = -(totalLines - 1) * (lineHeight / 2);
        return startY + d.index * lineHeight + (d.parent.data.currentFontSize / 4); 
    })
    .attr('text-anchor', 'middle') // Căn giữa text
    // Thay đổi ở đây: Xác định màu chữ dựa trên màu nền của node
    .style('fill', d => {
        const nodeColor = d.parent.data.color || "#fff"; // Lấy màu nền của node
        if (d.parent.data.type === 'root_node') {
             // Node gốc luôn là màu trắng (như bạn đã định nghĩa trước đó)
             return 'white';
        } else {
             // Các node khác: kiểm tra độ sáng của màu nền
             return this.isLightColor(nodeColor) ? '#333' : 'white'; // #333 là màu đen đậm hơn một chút
        }
    })
    .style('font-size', d => `${d.parent.data.currentFontSize}px`) // Áp dụng kích thước font đã lưu
    .style('font-weight', 'bold') // In đậm chữ khi render
    .style('font-family', 'K2D, sans-serif') // Áp dụng font K2D khi render
    .text(d => d.line);


    // Xử lý sự kiện hover
    nodeEnter.on('mouseover', (event, d) => {
        if (d.data.summarized_paragraph) {
            this.tooltip.content = d.data.summarized_paragraph;
            this.tooltip.visible = true;

            const nodeBBox = event.currentTarget.getBoundingClientRect();
            const containerBBox = this.$refs.mindmapArea.getBoundingClientRect();

            let tooltipX = nodeBBox.left + nodeBBox.width / 2;
            let tooltipY = nodeBBox.top;

            const tooltipWidth = 400; 
            const tooltipHeight = 100; 

            if (tooltipX + tooltipWidth / 2 > window.innerWidth) {
                tooltipX = window.innerWidth - tooltipWidth / 2 - 10;
            }
            if (tooltipX - tooltipWidth / 2 < 0) {
                tooltipX = tooltipWidth / 2 + 10;
            }

            if (tooltipY - tooltipHeight < 0) {
                tooltipY = nodeBBox.bottom + 10; 
            }

            this.tooltip.x = tooltipX;
            this.tooltip.y = tooltipY;
        }
    })
        .on('mouseout', () => {
            this.tooltip.visible = false;
        });

    // Tự động căn giữa mindmap khi load lần đầu
    this.centerMindmap();
        },
        isLightColor(hexColor) {
        // Chuyển đổi màu hex sang RGB
        let r = 0, g = 0, b = 0;
        if (hexColor.length === 4) { // #RGB
            r = parseInt(hexColor[1] + hexColor[1], 16);
            g = parseInt(hexColor[2] + hexColor[2], 16);
            b = parseInt(hexColor[3] + hexColor[3], 16);
        } else if (hexColor.length === 7) { // #RRGGBB
            r = parseInt(hexColor.substring(1, 3), 16);
            g = parseInt(hexColor.substring(3, 5), 16);
            b = parseInt(hexColor.substring(5, 7), 16);
        }
        // Tính toán độ sáng tương đối (Luminance)
        // Công thức W3C cho độ sáng tương đối: L = 0.2126 * R + 0.7152 * G + 0.0722 * B
        const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
        // Ngưỡng độ sáng: thường là 0.5. Nếu lớn hơn 0.5 là màu sáng, ngược lại là tối.
        return luminance > 0.5;
    },
        cleanupMindmap() {
            if (this.svg) {
                this.svg.selectAll("*").remove();
            }
            this.tooltip.visible = false;
        },
        zoomIn() {
            const newScale = this.transform.k * 1.2;
            this.svg.transition().duration(200).call(this.zoomBehavior.scaleTo, newScale);
        },
        zoomOut() {
            const newScale = this.transform.k / 1.2;
            this.svg.transition().duration(200).call(this.zoomBehavior.scaleTo, newScale);
        },
        resetZoom() {
            this.centerMindmap();
        },
        centerMindmap() {
            // Sử dụng prop 'data' thay vì 'rawData'
            if (this.data.length === 0 || !this.processedTreeData || !this.svg || !this.g) {
                return;
            }

            // Tạo một tree layout tạm thời để tính toán kích thước bao quanh
            // Sử dụng cùng cấu hình separation để tính toán bounding box chính xác
            const tempTreeLayout = d3.tree()
                .nodeSize([this.verticalNodeSeparation, this.horizontalNodeSeparation])
                .separation((a, b) => {
                    if (a.parent === b.parent) {
                        return 1.5;
                    } else {
                        return 3;
                    }
                });

            const root = tempTreeLayout(this.processedTreeData);

            let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

            root.descendants().forEach(d => {
                const nodeWidth = d.data.nodeCalculatedWidth;
                const nodeHeight = d.data.nodeCalculatedHeight;
                const halfWidth = nodeWidth / 2;
                const halfHeight = nodeHeight / 2;

                // Cập nhật min/max dựa trên kích thước thực của node
                minX = Math.min(minX, d.y - halfWidth);
                maxX = Math.max(maxX, d.y + halfWidth);
                minY = Math.min(minY, d.x - halfHeight);
                maxY = Math.max(maxY, d.x + halfHeight);
            });

            const graphWidth = maxX - minX;
            const graphHeight = maxY - minY;

            // Tính toán scale để vừa với màn hình, không phóng to quá 100% nếu mindmap nhỏ
            const scale = Math.min(this.svgWidth / graphWidth * 0.9, this.svgHeight / graphHeight * 0.9, 1); // Thêm 0.9 để có khoảng trống

            const translateX = this.svgWidth / 2 - (minX + maxX) / 2 * scale;
            const translateY = this.svgHeight / 2 - (minY + maxY) / 2 * scale;

            const newTransform = d3.zoomIdentity.translate(translateX, translateY).scale(scale);

            this.svg.transition().duration(750).call(this.zoomBehavior.transform, newTransform);
        }
    }
};
</script>

<style scoped>
.mindmap-viewer-container {
    width: 100%;
    height: 100%;
    position: relative;
    overflow: hidden;
}

.no-data-message {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    background: #f5f5f5;
    border-radius: 8px;
}

.no-data-message p {
    color: #666;
    font-size: 16px;
    text-align: center;
    margin: 0;
}

.mindmap-area {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: #fafafa;
}

.zoom-controls {
    position: absolute;
    top: 15px;
    right: 15px;
    z-index: 10;
    display: flex;
    gap: 8px;
}

.zoom-controls button {
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 6px;
    padding: 8px 12px;
    cursor: pointer;
    font-size: 16px;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: all 0.2s ease;
    min-width: 36px;
    min-height: 36px;
}

.zoom-controls button:hover {
    background: rgba(255, 255, 255, 1);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transform: translateY(-1px);
}

.zoom-controls button:active {
    transform: translateY(0);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

/* SVG chiếm toàn bộ không gian */
svg {
    display: block;
    width: 100%;
    height: 100%;
}

/* Kiểu cho các đường nối */
.link {
    stroke-linecap: round;
    transition: stroke-width 0.2s ease;
}

.link:hover {
    stroke-width: 3;
}

/* Kiểu cho nhóm node */
.node {
    cursor: pointer;
    transition: all 0.2s ease;
}

/* Kiểu cho hình chữ nhật của node */
.node-rect {
    transition: all 0.2s ease;
}

.node:hover .node-rect {
    filter: brightness(1.1);
    stroke-width: 3;
}

/* Kiểu cho text của node */
.node-text {
    font-size: 15px;
    font-weight: 700;
    fill: #333;
    user-select: none;
    pointer-events: none;
    text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
}

/* Màu chữ cho root node */
.node-root_node .node-rect {
    stroke: #2c3e50;
    stroke-width: 3;
}

.node-root_node .node-text {
    fill: white;
    font-weight: 800;
    font-size: 16px;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
}

/* Tooltip style */
.mindmap-tooltip {
    position: fixed;
    background: linear-gradient(135deg, rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.8));
    color: #fff;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.5;
    max-width: 400px;
    min-width: 200px;
    word-wrap: break-word;
    word-break: break-word;
    white-space: normal;
    pointer-events: none;
    z-index: 1000;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
}
</style>