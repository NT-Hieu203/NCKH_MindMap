<template>
    <div class="mindmap-viewer-container">
        <div v-if="!data || data.length === 0" class="no-data-message">
            <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-git-branch">
                <line x1="6" y1="3" x2="6" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path>
            </svg>
            <h3>Sơ đồ tư duy của bạn đang tải lên</h3>
            <p>Hãy đãm bảo rằng tài liệu PDF được tải để bắt đầu tạo mindmap.</p>
        </div>

        <div v-else class="mindmap-area" ref="mindmapArea">
            <svg ref="mindmapSvg"></svg>
            <div class="zoom-controls">
                <button @click="zoomIn" title="Phóng to">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
                </button>
                <button @click="zoomOut" title="Thu nhỏ">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
                </button>
                 <button @click="expandAll" title="Mở rộng tất cả">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path></svg>
                </button>
                <button @click="resetZoom" title="Căn giữa">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M3 12h1m8-9v1m8 8h1m-9 8v1M5.6 5.6l.7.7m12.1-.7l-.7.7m0 12.1l.7.7m-12.1 0l-.7.7"></path></svg>
                </button>
            </div>
            <div v-if="tooltip.visible" :style="tooltipStyle" class="mindmap-tooltip">
                {{ tooltip.content }}
            </div>
        </div>
    </div>
</template>

<script>
// ... (Phần script không thay đổi logic, chỉ cập nhật vị trí expander)
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
            hierarchyRoot: null,
            svg: null,
            g: null,
            zoomBehavior: null,
            nodeColors: ["#3b82f6", "#ef4444", "#10b981", "#f97316", "#8b5cf6", "#ec4899"],
            rootNodeColor: "#111827",
            tooltip: {
                visible: false,
                content: '',
                x: 0,
                y: 0
            },
            transitionDuration: 500,
            nodeWidth: 160,
            nodeHeight: 50,
            transitionDuration:300,
        };
    },
    // ... (computed, watch, mounted, beforeUnmount không đổi)
    computed: {
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
            handler(newData) {
                if (newData && newData.length > 0) {
                    this.$nextTick(() => {
                        this.processDataAndInitialize();
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
        window.addEventListener('resize', this.handleResize);
    },
    beforeUnmount() {
        window.removeEventListener('resize', this.handleResize);
    },
    methods: {
        processDataAndInitialize() {
            if (!this.data || this.data.length === 0) return;

            const dataMap = new Map(this.data.map(d => [d.index, { ...d, children: [] }]));
            let rootObject = null;
            this.data.forEach(item => {
                if (item.parent_index === -1) {
                    rootObject = dataMap.get(item.index);
                } else {
                    const parent = dataMap.get(item.parent_index);
                    if (parent) {
                        parent.children.push(dataMap.get(item.index));
                    }
                }
            });

            if (!rootObject) return;

            rootObject.color = this.rootNodeColor;
            rootObject.children.forEach((mainBranch, i) => {
                const color = this.nodeColors[i % this.nodeColors.length];
                const assignBranchColor = node => {
                    node.color = color;
                    if (node.children) node.children.forEach(assignBranchColor);
                };
                assignBranchColor(mainBranch);
            });

            this.initializeD3(rootObject);
        },

        initializeD3(rootObject) {
            if (this.svg) this.svg.selectAll("*").remove();
            const container = this.$refs.mindmapArea;
            if (!container) return;

            const width = container.clientWidth;
            const height = container.clientHeight;

            this.svg = d3.select(this.$refs.mindmapSvg)
                .attr("width", width)
                .attr("height", height)
                .attr("viewBox", [-width / 2, -height / 2, width, height]);

            this.g = this.svg.append("g");

            this.zoomBehavior = d3.zoom()
                .scaleExtent([0.1, 4])
                .on("zoom", (event) => {
                    this.g.attr("transform", event.transform);
                });

            this.svg.call(this.zoomBehavior);

            this.hierarchyRoot = d3.hierarchy(rootObject, d => d.children);
            this.hierarchyRoot.x0 = height / 2;
            this.hierarchyRoot.y0 = 0;

            this.hierarchyRoot.descendants().forEach(d => {
                d._children = d.children;
                if (d.depth > 1) {
                    d.children = null;
                }
            });

            this.update(this.hierarchyRoot);
            this.centerOnNode(this.hierarchyRoot);
        },

        update(source) {
            const treeLayout = d3.tree().nodeSize([this.nodeHeight + 40, this.nodeWidth + 80]);
            treeLayout(this.hierarchyRoot);

            const nodes = this.hierarchyRoot.descendants().reverse();
            const links = this.hierarchyRoot.links();

            const node = this.g.selectAll("g.node")
                .data(nodes, d => d.data.index);

            const nodeEnter = node.enter().append("g")
                .attr("class", "node")
                .attr("transform", `translate(${source.y0},${source.x0})`)
                .on('mouseover', (event, d) => this.showTooltip(event, d))
                .on('mouseout', () => this.hideTooltip());

            // SỬA ĐỔI: Quay lại thiết kế node nền màu
            nodeEnter.append("foreignObject")
                .attr("width", this.nodeWidth)
                .attr("height", this.nodeHeight)
                .attr("x", -this.nodeWidth / 2)
                .attr("y", -this.nodeHeight / 2)
                .style("overflow", "visible")
                .append("xhtml:div")
                .attr("class", "node-label-wrapper")
                .style("width", `${this.nodeWidth}px`)
                .style("height", `${this.nodeHeight}px`)
                .style("background-color", d => d.data.color || '#ccc')
                .html(d => `<div class="node-label">${d.data.keyword}</div>`);

            // SỬA ĐỔI: Đặt nút expander ở góc trên bên phải của node
            const expander = nodeEnter.append("g")
                .attr("class", "expander")
                // Vị trí mới: Góc trên-phải, có offset vào trong 1 chút
                .attr("transform", `translate(${this.nodeWidth / 1.58}, ${-this.nodeHeight / 3.58})`)
                .style("cursor", "pointer")
                .on("click", (event, d) => {
                    event.stopPropagation();
                    this.toggleNode(d);
                })
                .style("display", d => d._children ? "block" : "none");

            expander.append("rect")
                    .attr("x", -11)
                    .attr("y", -11)
                    .attr("width", 22)
                    .attr("height", 22)
                    .attr("rx", 8)
                    .attr("ry", 8)
                    .attr("class", "expander-rect");

            expander.append("text")
                .attr("class", "expander-text")
                .attr("dy", "0.35em")
                .text(d => d.children ? "−" : "+");

            const nodeUpdate = node.merge(nodeEnter).transition()
                .duration(this.transitionDuration)
                .attr("transform", d => `translate(${d.y},${d.x})`);
            
            nodeUpdate.select(".expander text").text(d => d.children ? "−" : "+");
            nodeUpdate.select(".expander").style("display", d => d._children || d.children ? "block" : "none");

            node.exit().transition()
                .duration(this.transitionDuration)
                .attr("transform", `translate(${source.y},${source.x})`)
                .style("opacity", 0)
                .remove();
            
            // ... (Phần xử lý link không đổi)
            const link = this.g.selectAll("path.link")
                .data(links, d => d.target.data.index);

            const linkEnter = link.enter().insert("path", "g")
                .attr("class", "link")
                .attr("d", d => {
                    const o = { x: source.x0 || 0, y: source.y0 || 0 };
                    return d3.linkHorizontal()({ source: o, target: o });
                });

            link.merge(linkEnter).transition()
                .duration(this.transitionDuration)
                .attr("d", d3.linkHorizontal().x(d => d.y).y(d => d.x));

            link.exit().transition()
                .duration(this.transitionDuration)
                .attr("d", d => {
                    const o = { x: source.x, y: source.y };
                    return d3.linkHorizontal()({ source: o, target: o });
                })
                .remove();

            nodes.forEach(d => {
                d.x0 = d.x;
                d.y0 = d.y;
            });
        },
        // ... (Các methods còn lại không đổi)
        toggleNode(d) {
            if (d.children) {
                d._children = d.children;
                d.children = null;
            } else {
                d.children = d._children;
                d._children = null;
            }
            this.update(d);
        },

         expandAll() {
            if (!this.hierarchyRoot) return;
            
            if (this.isFullyExpanded) {
                // Nếu đang bung hết -> Thu lại
                this.collapseAll();
            } else {
                // Nếu đang thu -> Bung ra
                const expandRecursive = (node) => {
                if (node._children) {
                    node.children = node._children;
                    node._children = null;
                }
                if (node.children) {
                    node.children.forEach(expandRecursive);
                }
            };
            expandRecursive(this.hierarchyRoot);
            this.update(this.hierarchyRoot);
            }

            // Đảo ngược trạng thái
            this.isFullyExpanded = !this.isFullyExpanded;
        },

        // SỬA ĐỔI LOGIC 3: Hàm mới để thu gọn mindmap về ban đầu
        collapseAll() {
            if (!this.hierarchyRoot) return;
            const originalDuration = this.transitionDuration;
            this.transitionDuration = 150; // Giảm animation lúc collapse
            this.hierarchyRoot.descendants().forEach(d => {
                // Thu gọn tất cả các node từ cấp 1 trở đi
                if (d.depth >= 1) { 
                    if (d.children) {
                        d._children = d.children;
                        d.children = null;
                    }
                }
            });
            this.update(this.hierarchyRoot);
            setTimeout(() => {
                this.transitionDuration = originalDuration;
            }, 200);
        },

        showTooltip(event, d) {
            if (d.data.summarized_paragraph) {
                this.tooltip.content = d.data.summarized_paragraph;
                this.tooltip.visible = true;
                this.tooltip.x = event.pageX;
                this.tooltip.y = event.pageY;
            }
        },
        hideTooltip() {
            this.tooltip.visible = false;
        },

        handleResize() {
            if (!this.svg) return;
            const container = this.$refs.mindmapArea;
            if (!container) return;
            const width = container.clientWidth;
            const height = container.clientHeight;
            this.svg.attr("width", width).attr("height", height)
                .attr("viewBox", [-width / 2, -height / 2, width, height]);
        },
        zoomIn() { if(this.zoomBehavior && this.svg) this.svg.transition().duration(200).call(this.zoomBehavior.scaleBy, 1.2); },
        zoomOut() { if(this.zoomBehavior && this.svg) this.svg.transition().duration(200).call(this.zoomBehavior.scaleBy, 0.8); },
        resetZoom() { this.centerOnNode(this.hierarchyRoot); },
        centerOnNode(node) {
            if (!this.svg || !this.g || !node || !this.zoomBehavior) return;
            const t = d3.zoomTransform(this.svg.node());
            this.svg.transition().duration(750)
                .call(this.zoomBehavior.translateTo, 0, 0);
        },
        cleanupMindmap() {
            if (this.svg) this.svg.selectAll("*").remove();
            this.hierarchyRoot = null;
        }
    }
};
</script>

<style scoped>
/* Font chữ hiện đại và dễ đọc */
.mindmap-viewer-container {
    width: 100%;
    height: 100%;
    position: relative;
    overflow: hidden;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background-color: #f8fafc;
}

.mindmap-area {
    width: 100%;
    height: 100%;
}

/* Thông báo "Không có dữ liệu" thân thiện hơn */
.no-data-message {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    color: #64748b;
    text-align: center;
}
.no-data-message svg {
    color: #94a3b8;
    margin-bottom: 1.5rem;
}
.no-data-message h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: #1e293b;
    margin: 0 0 0.5rem 0;
}
.no-data-message p {
    font-size: 1rem;
    margin: 0;
}

/* SỬA ĐỔI: Chuyển bảng điều khiển lên góc trên bên phải */
.zoom-controls {
    position: absolute;
    top: 20px; /* Vị trí mới */
    right: 20px;
    z-index: 10;
    display: flex;
    gap: 10px;
    padding: 10px;
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
}

.zoom-controls button {
    background: rgba(255, 255, 255, 0.5);
    border: 1px solid transparent;
    border-radius: 8px;
    width: 40px;
    height: 40px;
    cursor: pointer;
    color: #1e293b;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease-in-out;
}

.zoom-controls button:hover {
    background: white;
    transform: translateY(-2px);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    color: #3b82f6;
}

.mindmap-tooltip {
    position: fixed;
    background: rgba(29, 41, 59, 0.9);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    color: #f8fafc;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.5;
    max-width: 320px;
    pointer-events: none;
    z-index: 1000;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Style cho các thành phần D3 */
:deep(.link) {
    fill: none;
    stroke: #cbd5e1;
    stroke-width: 1.5px;
    stroke-opacity: 0.8;
}

:deep(.node) {
    cursor: pointer;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
    transition: filter 0.3s ease;
}

:deep(.node:hover) {
    filter: drop-shadow(0 5px 10px rgba(0,0,0,0.15));
}

/* SỬA ĐỔI: Thiết kế node nền màu */
:deep(.node-label-wrapper) {
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    /* Giảm padding để có thêm không gian cho nút expander */
    padding: 8px 24px 8px 8px;
    transition: all 0.3s ease;
    /* background-color được set bằng D3 */
}

:deep(.node-label) {
    color: white; /* Text màu trắng trên nền màu */
    font-weight: 500;
    font-size: 14px;
    line-height: 1.4;
    max-height: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}

/* SỬA ĐỔI: Style cho nút +/- trên nền màu */
:deep(.expander-rect) {
    fill: rgba(255, 255, 255, 0.2); /* Nền mờ để không quá chói */
    transition: all 0.2s ease;
    fill: transparent;
}
:deep(.expander-text) {
    text-anchor: middle;
    font-size: 18px;
    font-weight: 400;
    pointer-events: none;
    fill: rgba(255, 255, 255, 0.9); /* Màu chữ trắng mờ */
}
:deep(.expander:hover .expander-rect) {
    fill: rgba(255, 255, 255, 0.4);
}
:deep(.expander:hover .expander-text) {
    fill: black;
}
</style>