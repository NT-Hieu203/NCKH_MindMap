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
        data: {
            type: Array,
            default: () => []
        }
    },
    data() {
        return {
            svgWidth: 800,
            svgHeight: 600,
            svg: null,
            g: null,
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
            // Cấu hình động cho node và khoảng cách
            nodePadding: { horizontal: 25, vertical: 20 },
            minNodeWidth: 140,
            maxNodeWidth: 280,
            nodeHeightPerLine: 22,
            minNodeHeight: 50,
            // Các giá trị này sẽ được tính toán động
            calculatedHorizontalSeparation: 350,
            calculatedVerticalSeparation: 120,
        };
    },
    computed: {
        processedTreeData() {
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
                transform: 'translate(-50%, -110%)',
                display: this.tooltip.visible ? 'block' : 'none',
            };
        }
    },
    watch: {
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
                    this.setupMindmap();
                }
            }
        },

        // Tính toán kích thước động cho mindmap
        calculateDynamicSpacing() {
            if (!this.processedTreeData) return;

            // Đếm số node và tính toán độ sâu của cây
            let nodeCount = 0;
            let maxDepth = 0;
            let maxChildrenAtLevel = 0;
            const levelCounts = {};

            this.processedTreeData.each(d => {
                nodeCount++;
                maxDepth = Math.max(maxDepth, d.depth);
                
                if (!levelCounts[d.depth]) {
                    levelCounts[d.depth] = 0;
                }
                levelCounts[d.depth]++;
                maxChildrenAtLevel = Math.max(maxChildrenAtLevel, levelCounts[d.depth]);
            });

            // Tính toán khoảng cách dựa trên kích thước container và số lượng node
            const containerAspectRatio = this.svgWidth / this.svgHeight;
            const targetAspectRatio = 1.6; // Tỷ lệ hình chữ nhật lý tưởng

            // Điều chỉnh khoảng cách ngang
            const baseHorizontalSeparation = 200;
            const maxHorizontalSeparation = 500;
            const minHorizontalSeparation = 150;

            // Tính toán dựa trên chiều rộng container và số level
            let horizontalFactor = this.svgWidth / (maxDepth * baseHorizontalSeparation);
            horizontalFactor = Math.max(0.5, Math.min(2, horizontalFactor));
            
            this.calculatedHorizontalSeparation = Math.max(
                minHorizontalSeparation,
                Math.min(maxHorizontalSeparation, baseHorizontalSeparation * horizontalFactor)
            );

            // Điều chỉnh khoảng cách dọc
            const baseVerticalSeparation = 80;
            const maxVerticalSeparation = 200;
            const minVerticalSeparation = 60;

            // Tính toán dựa trên chiều cao container và số node trên mỗi level
            let verticalFactor = this.svgHeight / (maxChildrenAtLevel * baseVerticalSeparation);
            verticalFactor = Math.max(0.6, Math.min(2.5, verticalFactor));

            this.calculatedVerticalSeparation = Math.max(
                minVerticalSeparation,
                Math.min(maxVerticalSeparation, baseVerticalSeparation * verticalFactor)
            );

            // Điều chỉnh để đạt được tỷ lệ hình chữ nhật mong muốn
            if (containerAspectRatio > targetAspectRatio) {
                // Container rộng hơn mong muốn -> tăng khoảng cách ngang
                this.calculatedHorizontalSeparation *= 1.2;
            } else if (containerAspectRatio < targetAspectRatio) {
                // Container cao hơn mong muốn -> tăng khoảng cách dọc
                this.calculatedVerticalSeparation *= 1.2;
            }

            console.log(`Dynamic spacing calculated: H=${this.calculatedHorizontalSeparation.toFixed(0)}, V=${this.calculatedVerticalSeparation.toFixed(0)}`);
        },

        setupMindmap() {
            if (this.svg) {
                this.svg.selectAll("*").remove();
            } else {
                this.svg = d3.select(this.$refs.mindmapSvg);
            }

            this.g = this.svg.append('g');

            this.zoomBehavior = d3.zoom()
                .scaleExtent([0.1, 4])
                .on("zoom", event => {
                    this.transform = event.transform;
                    this.g.attr("transform", this.transform);
                });
            this.svg.call(this.zoomBehavior);

            // Tính toán khoảng cách động trước khi xử lý text
            this.calculateDynamicSpacing();

            // Tiền xử lý text để tính toán kích thước node
            const tempSvg = d3.select("body").append("svg").style("position", "absolute").style("left", "-9999px");
            const tempText = tempSvg.append("text")
                .attr("class", "node-text")
                .style("font-weight", "bold")
                .style("font-family", "K2D, sans-serif");

            this.processedTreeData.each(d => {
                const fontSize = d.data.type === 'root_node' ? 20 : 18;
                tempText.style("font-size", `${fontSize}px`);

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
                maxWidth = Math.max(maxWidth, tempText.text(currentLine).node().getComputedTextLength());

                d.data.wrappedKeyword = wrappedLines;
                d.data.nodeCalculatedWidth = Math.max(this.minNodeWidth, maxWidth + this.nodePadding.horizontal * 2);
                d.data.nodeCalculatedHeight = Math.max(this.minNodeHeight, lineCount * (fontSize * 1.2) + this.nodePadding.vertical * 2);
                d.data.currentFontSize = fontSize;
            });

            tempSvg.remove();

            // Thiết lập Tree Layout với khoảng cách động
            const treeLayout = d3.tree()
                .nodeSize([this.calculatedVerticalSeparation, this.calculatedHorizontalSeparation])
                .separation((a, b) => {
                    // Tính toán separation động dựa trên kích thước node thực tế
                    const nodeWidthA = a.data.nodeCalculatedWidth || this.minNodeWidth;
                    const nodeWidthB = b.data.nodeCalculatedWidth || this.minNodeWidth;
                    const nodeHeightA = a.data.nodeCalculatedHeight || this.minNodeHeight;
                    const nodeHeightB = b.data.nodeCalculatedHeight || this.minNodeHeight;

                    // Tính toán hệ số separation dựa trên kích thước container
                    const baseSeparation = a.parent === b.parent ? 1.2 : 2.5;
                    const sizeFactor = Math.max(nodeWidthA, nodeWidthB) / this.minNodeWidth;
                    const containerFactor = Math.min(this.svgWidth, this.svgHeight) / 600; // Base size 600px

                    return baseSeparation * sizeFactor * Math.max(0.7, containerFactor);
                });

            const root = treeLayout(this.processedTreeData);

            // Render các đường nối
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

            // Render các nút
            const nodeEnter = this.g.selectAll('.node')
                .data(root.descendants())
                .enter()
                .append('g')
                .attr('class', d => `node node-${d.data.type}`)
                .attr('transform', d => `translate(${d.y}, ${d.x})`);

            // Thêm hình chữ nhật
            nodeEnter.append('rect')
                .attr('class', 'node-rect')
                .attr('rx', 8)
                .attr('ry', 8)
                .attr('width', d => d.data.nodeCalculatedWidth)
                .attr('height', d => d.data.nodeCalculatedHeight)
                .attr('x', d => -d.data.nodeCalculatedWidth / 2)
                .attr('y', d => -d.data.nodeCalculatedHeight / 2)
                .attr('fill', d => d.data.color || "#fff")
                .attr('stroke', '#999')
                .attr('stroke-width', 2);

            // Thêm text đã xuống dòng
            nodeEnter.selectAll('.node-text')
                .data(d => d.data.wrappedKeyword.map((line, i) => ({ line: line, parent: d, index: i })))
                .enter()
                .append('text')
                .attr('class', 'node-text')
                .attr('x', 0)
                .attr('y', (d) => {
                    const totalLines = d.parent.data.wrappedKeyword.length;
                    const lineHeight = d.parent.data.currentFontSize * 1.2;
                    const startY = -(totalLines - 1) * (lineHeight / 2);
                    return startY + d.index * lineHeight + (d.parent.data.currentFontSize / 4);
                })
                .attr('text-anchor', 'middle')
                .style('fill', d => {
                    const nodeColor = d.parent.data.color || "#fff";
                    if (d.parent.data.type === 'root_node') {
                        return 'white';
                    } else {
                        return this.isLightColor(nodeColor) ? '#333' : 'white';
                    }
                })
                .style('font-size', d => `${d.parent.data.currentFontSize}px`)
                .style('font-weight', 'bold')
                .style('font-family', 'K2D, sans-serif')
                .text(d => d.line);

            // Xử lý sự kiện hover
            nodeEnter.on('mouseover', (event, d) => {
                if (d.data.summarized_paragraph) {
                    this.tooltip.content = d.data.summarized_paragraph;
                    this.tooltip.visible = true;

                    const nodeBBox = event.currentTarget.getBoundingClientRect();
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

            // Tự động căn giữa mindmap với tỷ lệ phù hợp
            this.centerMindmapWithOptimalView();
        },

        isLightColor(hexColor) {
            let r = 0, g = 0, b = 0;
            if (hexColor.length === 4) {
                r = parseInt(hexColor[1] + hexColor[1], 16);
                g = parseInt(hexColor[2] + hexColor[2], 16);
                b = parseInt(hexColor[3] + hexColor[3], 16);
            } else if (hexColor.length === 7) {
                r = parseInt(hexColor.substring(1, 3), 16);
                g = parseInt(hexColor.substring(3, 5), 16);
                b = parseInt(hexColor.substring(5, 7), 16);
            }
            const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
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
            this.centerMindmapWithOptimalView();
        },

        centerMindmapWithOptimalView() {
            if (this.data.length === 0 || !this.processedTreeData || !this.svg || !this.g) {
                return;
            }

            // Tạo tree layout tạm thời với khoảng cách động
            const tempTreeLayout = d3.tree()
                .nodeSize([this.calculatedVerticalSeparation, this.calculatedHorizontalSeparation])
                .separation((a, b) => {
                    const nodeWidthA = a.data.nodeCalculatedWidth || this.minNodeWidth;
                    const nodeWidthB = b.data.nodeCalculatedWidth || this.minNodeWidth;
                    const baseSeparation = a.parent === b.parent ? 1.2 : 2.5;
                    const sizeFactor = Math.max(nodeWidthA, nodeWidthB) / this.minNodeWidth;
                    const containerFactor = Math.min(this.svgWidth, this.svgHeight) / 600;
                    return baseSeparation * sizeFactor * Math.max(0.7, containerFactor);
                });

            const root = tempTreeLayout(this.processedTreeData);

            // Chỉ focus vào node gốc và các node con cấp 1 và 2
            const focusNodes = [];
            root.descendants().forEach(d => {
                if (d.depth <= 2) { // Node gốc (depth 0), cấp 1, và cấp 2
                    focusNodes.push(d);
                }
            });

            if (focusNodes.length === 0) {
                focusNodes.push(root); // Fallback nếu không có node nào
            }

            // Tính toán bounding box chỉ cho các node focus
            let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

            focusNodes.forEach(d => {
                const nodeWidth = d.data.nodeCalculatedWidth;
                const nodeHeight = d.data.nodeCalculatedHeight;
                const halfWidth = nodeWidth / 2;
                const halfHeight = nodeHeight / 2;

                minX = Math.min(minX, d.y - halfWidth);
                maxX = Math.max(maxX, d.y + halfWidth);
                minY = Math.min(minY, d.x - halfHeight);
                maxY = Math.max(maxY, d.x + halfHeight);
            });

            const focusWidth = maxX - minX;
            const focusHeight = maxY - minY;

            // Tính toán scale để hiển thị rõ ràng khu vực focus
            const padding = 0.2; // 20% padding để tạo không gian thoải mái
            const minScale = 0.8; // Scale tối thiểu để đảm bảo text đọc được
            const maxScale = 2.0; // Scale tối đa để không phóng to quá
            
            const scaleX = (this.svgWidth * (1 - padding)) / focusWidth;
            const scaleY = (this.svgHeight * (1 - padding)) / focusHeight;
            let scale = Math.min(scaleX, scaleY);
            
            // Giới hạn scale trong khoảng hợp lý
            scale = Math.max(minScale, Math.min(maxScale, scale));

            // Căn giữa khu vực focus
            const focusCenterX = (minX + maxX) / 2;
            const focusCenterY = (minY + maxY) / 2;
            
            const translateX = this.svgWidth / 2 - focusCenterX * scale;
            const translateY = this.svgHeight / 2 - focusCenterY * scale;

            const newTransform = d3.zoomIdentity.translate(translateX, translateY).scale(scale);

            this.svg.transition().duration(750).call(this.zoomBehavior.transform, newTransform);
            
            console.log(`Focus view: ${focusNodes.length} nodes, scale: ${scale.toFixed(2)}`);
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

svg {
    display: block;
    width: 100%;
    height: 100%;
}

.link {
    stroke-linecap: round;
    transition: stroke-width 0.2s ease;
}

.link:hover {
    stroke-width: 3;
}

.node {
    cursor: pointer;
    transition: all 0.2s ease;
}

.node-rect {
    transition: all 0.2s ease;
}

.node:hover .node-rect {
    filter: brightness(1.1);
    stroke-width: 3;
}

.node-text {
    font-size: 15px;
    font-weight: 700;
    fill: #333;
    user-select: none;
    pointer-events: none;
    text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
}

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