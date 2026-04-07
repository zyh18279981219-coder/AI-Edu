<template>
  <div class="home-shell">
    <PageHero
        eyebrow="Learning Hub"
        title="学习首页"
        description="围绕课程知识图谱、当前学习进度和待学习节点，帮助你快速定位下一步该学什么。"
        :badges="heroBadges"
        tone="learning"
    >
      <template #actions>
        <RouterLink class="primary-link" :to="continueLearningRoute">继续学习</RouterLink>
        <RouterLink class="ghost-btn" to="/learning">查看学习计划</RouterLink>
      </template>
    </PageHero>

    <section v-if="error" class="state-card error-state">
      <h2>首页加载失败</h2>
      <p>{{ error }}</p>
    </section>

    <template v-else>
      <section class="metric-grid home-metric-grid">
        <MetricStatCard
            label="章节进度"
            :value="formatPercent(progress?.chapters.progress)"
            :description="`已完成 ${progress?.chapters.completed ?? 0} / ${progress?.chapters.total ?? 0} 个章节`"
            tone="brand"
        />
        <MetricStatCard
            label="小节进度"
            :value="formatPercent(progress?.sections.progress)"
            :description="`已完成 ${progress?.sections.completed ?? 0} / ${progress?.sections.total ?? 0} 个小节`"
            tone="success"
        />
        <MetricStatCard
            label="知识点进度"
            :value="formatPercent(progress?.points.progress)"
            :description="`已完成 ${progress?.points.completed ?? 0} / ${progress?.points.total ?? 0} 个知识点`"
            tone="warning"
        />
        <MetricStatCard
            label="图谱规模"
            :value="graphStats.totalNodes"
            :description="`关系 ${graphStats.totalRelations} 条，叶子节点 ${graphStats.leafNodes} 个`"
        />
      </section>

      <section class="home-layout">
        <article class="card-panel home-graph-panel">
          <div class="section-head home-head">
            <div>
              <h2>知识图谱</h2>
              <span class="muted">点击图谱节点后，下方会同步定位到对应章节、小节或知识点。</span>
            </div>
            <div class="home-head-actions">
              <button type="button" class="ghost-btn" @click="focusCurrentTrack">定位当前节点</button>
              <button type="button" class="ghost-btn" @click="resetSelection">回到总览</button>
            </div>
          </div>

          <div v-if="loading" class="state-card">正在加载首页学习数据...</div>
          <template v-else>
            <div class="home-root-card">
              <div>
                <div class="home-root-kicker">课程总览</div>
                <h3>{{ graph?.name || "当前课程" }}</h3>
                <p>{{ selectedNodeDescription || "点击图谱或下方节点，可查看该知识点的说明和学习状态。" }}</p>
              </div>
              <div class="home-root-stats">
                <span class="info-pill">章节 {{ chapterNodes.length }}</span>
                <span class="info-pill">小节 {{ progress?.sections.total ?? 0 }}</span>
                <span class="info-pill">知识点 {{ progress?.points.total ?? 0 }}</span>
              </div>
            </div>

            <div class="home-visual-block">
              <div class="home-level-head">
                <div>
                  <h3>图谱视图</h3>
                  <span class="muted">先看章节，点击章节展开小节，点击小节继续展开知识点。</span>
                </div>
                <div class="home-head-actions">
                  <button type="button" class="ghost-btn" @click="collapseToCourse">收起到课程</button>
                  <button type="button" class="ghost-btn" @click="collapseToChapter" :disabled="!activeChapter">
                    收起到章节
                  </button>
                </div>
              </div>
              <div class="home-graph-breadcrumb">
                <button type="button" class="home-crumb" :class="{ active: !activeChapterKey }"
                        @click="collapseToCourse">
                  课程总览
                </button>
                <button
                    v-if="activeChapter"
                    type="button"
                    class="home-crumb"
                    :class="{ active: !!activeChapterKey && !activeSectionKey }"
                    @click="collapseToChapter"
                >
                  {{ activeChapter.name }}
                </button>
                <span v-if="activeSection" class="home-crumb home-crumb--static">{{ activeSection.name }}</span>
              </div>
              <div ref="graphChartRef" class="home-graph-canvas"></div>
            </div>

            <div class="home-level-block">
              <div class="home-level-head">
                <h3>章节</h3>
                <span class="muted">{{ chapterNodes.length }} 个章节</span>
              </div>
              <div class="home-chip-grid home-chip-grid--chapter">
                <button
                    v-for="chapter in chapterNodes"
                    :key="chapter.name"
                    type="button"
                    class="home-node-chip home-node-chip--chapter"
                    :class="{
                    active: activeChapterKey === chapter.name,
                    current: currentChapter?.name === chapter.name,
                    done: nodeFlag(chapter) === '1',
                  }"
                    @click="selectChapter(chapter)"
                >
                  <span class="home-node-title">{{ chapter.name }}</span>
                  <span class="home-node-meta">{{ nodeMeta(chapter, "章节") }}</span>
                </button>
              </div>
            </div>

            <div class="home-level-block">
              <div class="home-level-head">
                <h3>小节</h3>
                <span class="muted">{{ activeSections.length }} 个小节</span>
              </div>
              <div class="home-chip-grid">
                <button
                    v-for="section in activeSections"
                    :key="section.name"
                    type="button"
                    class="home-node-chip"
                    :class="{
                    active: activeSectionKey === section.name,
                    current: currentSection?.name === section.name,
                    done: nodeFlag(section) === '1',
                  }"
                    @click="selectSection(section)"
                >
                  <span class="home-node-title">{{ section.name }}</span>
                  <span class="home-node-meta">{{ nodeMeta(section, "小节") }}</span>
                </button>
                <div v-if="!activeSections.length" class="list-card">当前章节下暂无小节数据。</div>
              </div>
            </div>

            <div class="home-level-block">
              <div class="home-level-head">
                <h3>知识点</h3>
                <span class="muted">{{ activePoints.length }} 个知识点</span>
              </div>
              <div class="home-point-list">
                <button
                    v-for="point in activePoints"
                    :key="point.name"
                    type="button"
                    class="home-point-card"
                    :class="{
                    active: selectedNodeKey === point.name,
                    current: currentPoint?.name === point.name,
                    done: nodeFlag(point) === '1',
                  }"
                    @click="selectPoint(point)"
                >
                  <div>
                    <div class="home-node-title">{{ point.name }}</div>
                    <div class="home-node-meta">{{ nodeMeta(point, "知识点") }}</div>
                  </div>
                  <span class="pill" :class="nodeFlag(point) === '1' ? 'mastery-high' : 'mastery-mid'">
                    {{ nodeFlag(point) === "1" ? "已完成" : "进行中" }}
                  </span>
                </button>
                <div v-if="!activePoints.length" class="list-card">当前小节下暂无可展示的知识点。</div>
              </div>
            </div>
          </template>
        </article>

        <aside class="home-sidebar">
          <article class="card-panel home-progress-card">
            <div class="section-head">
              <h2>当前学习定位</h2>
              <span class="muted">自动根据未完成节点定位</span>
            </div>
            <div class="home-progress-stack">
              <div class="home-progress-item">
                <div class="home-progress-top">
                  <strong>当前章节</strong>
                  <span>{{ currentChapter?.name || "暂无" }}</span>
                </div>
                <div class="progress-line"><span :style="{ width: `${currentChapterPercent}%` }"></span></div>
                <small>{{ currentChapterProgressText }}</small>
              </div>
              <div class="home-progress-item">
                <div class="home-progress-top">
                  <strong>当前小节</strong>
                  <span>{{ currentSection?.name || "暂无" }}</span>
                </div>
                <div class="progress-line"><span :style="{ width: `${currentSectionPercent}%` }"></span></div>
                <small>{{ currentSectionProgressText }}</small>
              </div>
              <div class="home-progress-item">
                <div class="home-progress-top">
                  <strong>当前知识点</strong>
                  <span>{{ currentPoint?.name || "暂无" }}</span>
                </div>
                <div class="progress-line"><span :style="{ width: `${currentPointPercent}%` }"></span></div>
                <small>{{ currentPointProgressText }}</small>
              </div>
            </div>
          </article>

          <article class="card-panel home-detail-card">
            <div class="section-head">
              <h2>节点详情</h2>
              <span class="muted">{{ selectedNodeLabel }}</span>
            </div>
            <div class="home-detail-body">
              <h3>{{ selectedNodeTitle }}</h3>
              <p>{{ selectedNodeDescription || "暂无节点说明" }}</p>
              <div class="home-detail-meta">
                <span class="meta-chip">学习状态：{{ selectedNodeFlagText }}</span>
                <span class="meta-chip">平均掌握度：{{ selectedNodeStats.avgMastery }}%</span>
                <span class="meta-chip">平均完成度：{{ selectedNodeStats.avgCompletion }}%</span>
                <span class="meta-chip">平均学习时长：{{ selectedNodeStats.avgStudyDuration }} 分钟</span>
              </div>
            </div>
          </article>

          <article class="card-panel home-action-card">
            <div class="section-head">
              <h2>下一步建议</h2>
            </div>
            <div class="stack-list">
              <div class="list-card">
                <div class="list-title">优先进入当前知识点</div>
                <div class="list-meta">{{ currentPoint?.name || "暂无待学习知识点" }}</div>
                <RouterLink class="primary-link home-action-link" :to="continueLearningRoute">进入课程内容</RouterLink>
              </div>
              <div class="list-card">
                <div class="list-title">查看学习计划</div>
                <div class="list-meta">结合个性化路径和学习任务安排下一阶段学习。</div>
                <RouterLink class="ghost-btn home-action-link" to="/learning">打开我的学习</RouterLink>
              </div>
            </div>
          </article>
        </aside>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import {computed, nextTick, onBeforeUnmount, onMounted, ref, watch} from "vue";
import {RouterLink} from "vue-router";
import MetricStatCard from "../../components/ui/MetricStatCard.vue";
import PageHero from "../../components/ui/PageHero.vue";
import {type ECharts, init} from "../../lib/echarts";
import {GraphVisualizationResponse,LearningProgressResponse, GraphVisualizationNode} from "../../types/student";
import {fetchLearningProgress, fetchGraphVisualization} from '../../api/student';
import {CourseNode} from "../../types/knowledgeGraph";
import {fetchKnowledgeGraph} from "../../api/knowledgeGraph";

type CurrentNodeInfo = {
  name: string;
  index: number;
  total: number;
  completed: number;
};

const loading = ref(true);
const error = ref("");
const graph = ref<{ name?: string; children?: CourseNode[] } | null>(null);
const graphVisualization = ref<GraphVisualizationResponse | null>(null);
const progress = ref<LearningProgressResponse | null>(null);

const activeChapterKey = ref("");
const activeSectionKey = ref("");
const selectedNodeKey = ref("");

const currentChapter = ref<CurrentNodeInfo | null>(null);
const currentSection = ref<CurrentNodeInfo | null>(null);
const currentPoint = ref<CurrentNodeInfo | null>(null);

const graphChartRef = ref<HTMLDivElement | null>(null);
let graphChart: ECharts | null = null;

const chapterNodes = computed(() => graph.value?.children ?? []);
const allSections = computed(() => chapterNodes.value.flatMap((item) => item.grandchildren ?? []));
const allPoints = computed(() => allSections.value.flatMap((item) => item["great-grandchildren"] ?? []));

const activeChapter = computed(
    () => chapterNodes.value.find((item) => item.name === activeChapterKey.value) ?? chapterNodes.value[0] ?? null,
);
const activeSections = computed(() => activeChapter.value?.grandchildren ?? []);
const activeSection = computed(
    () => activeSections.value.find((item) => item.name === activeSectionKey.value) ?? activeSections.value[0] ?? null,
);
const activePoints = computed(() => activeSection.value?.["great-grandchildren"] ?? []);

const selectedNode = computed(
    () =>
        chapterNodes.value.find((item) => item.name === selectedNodeKey.value) ??
        allSections.value.find((item) => item.name === selectedNodeKey.value) ??
        allPoints.value.find((item) => item.name === selectedNodeKey.value) ??
        activeSection.value ??
        activeChapter.value ??
        null,
);

const graphNodeMap = computed(() => {
  const map = new Map<string, GraphVisualizationNode>();
  for (const node of graphVisualization.value?.mocKgNodeDtoList ?? []) {
    if (!map.has(node.nodeName)) {
      map.set(node.nodeName, node);
    }
  }
  return map;
});

const graphStats = computed(() => {
  const nodes = graphVisualization.value?.mocKgNodeDtoList ?? [];
  const relations = graphVisualization.value?.mocKgRelationDtoList ?? [];
  return {
    totalNodes: nodes.length,
    totalRelations: relations.length,
    leafNodes: nodes.filter((item) => (item.childCount ?? 0) === 0).length,
  };
});

const heroBadges = computed(() => [
  `章节 ${progress.value?.chapters.total ?? 0}`,
  `当前 ${currentPoint.value?.name ?? "未定位"}`,
  `关系 ${graphStats.value.totalRelations}`,
]);

const selectedNodeTitle = computed(() => selectedNode.value?.name || graph.value?.name || "当前课程");
const selectedNodeDescription = computed(() => {
  if (!selectedNode.value) return "";
  return graphNodeMap.value.get(selectedNode.value.name)?.description || selectedNode.value.description || "";
});
const selectedNodeLabel = computed(() => {
  if (!selectedNode.value) return "课程节点";
  if (allPoints.value.some((item) => item.name === selectedNode.value?.name)) return "知识点";
  if (allSections.value.some((item) => item.name === selectedNode.value?.name)) return "小节";
  if (chapterNodes.value.some((item) => item.name === selectedNode.value?.name)) return "章节";
  return "课程节点";
});
const selectedNodeFlagText = computed(() => (nodeFlag(selectedNode.value) === "1" ? "已完成" : "进行中"));
const selectedNodeStats = computed(() => {
  const mapped = selectedNode.value ? graphNodeMap.value.get(selectedNode.value.name) : null;
  return {
    avgMastery: mapped?.mocKgNodeAvgStatisticsDto?.avgMasteryRate ?? 0,
    avgCompletion: mapped?.mocKgNodeAvgStatisticsDto?.avgCompletionRate ?? 0,
    avgStudyDuration: mapped?.mocKgNodeAvgStatisticsDto?.avgLearnedTimeCount ?? 0,
  };
});

const currentChapterPercent = computed(() => computePercent(currentChapter.value));
const currentSectionPercent = computed(() => computePercent(currentSection.value));
const currentPointPercent = computed(() => computePercent(currentPoint.value));

const currentChapterProgressText = computed(() => currentText(currentChapter.value, "章节"));
const currentSectionProgressText = computed(() => currentText(currentSection.value, "小节"));
const currentPointProgressText = computed(() => currentText(currentPoint.value, "知识点"));

const continueLearningRoute = computed(() => {
  const nodeName = currentPoint.value?.name || selectedNode.value?.name;
  return nodeName
      ? {path: "/course-content", query: {node: nodeName, continue: "true"}}
      : {path: "/course-content", query: {continue: "true"}};
});

function nodeFlag(node?: CourseNode | null) {
  return node?.flag ?? "0";
}

function formatPercent(value?: number) {
  return `${Number(value ?? 0).toFixed(1)}%`;
}

function nodeMeta(node: CourseNode, label: string) {
  return `${label} · ${nodeFlag(node) === "1" ? "已完成" : "待继续"}`;
}

function computePercent(node: CurrentNodeInfo | null) {
  if (!node || !node.total) return 0;
  return Number(((node.completed / node.total) * 100).toFixed(1));
}

function currentText(node: CurrentNodeInfo | null, label: string) {
  if (!node) return `暂无${label}定位`;
  return `${label} ${node.index + 1}/${node.total} · 已完成 ${node.completed} 个`;
}

function selectChapter(chapter: CourseNode) {
  activeChapterKey.value = chapter.name;
  const firstSection = chapter.grandchildren?.[0];
  if (firstSection) {
    activeSectionKey.value = firstSection.name;
    selectedNodeKey.value = firstSection["great-grandchildren"]?.[0]?.name ?? firstSection.name;
  } else {
    activeSectionKey.value = "";
    selectedNodeKey.value = chapter.name;
  }
}

function selectSection(section: CourseNode) {
  activeSectionKey.value = section.name;
  selectedNodeKey.value = section["great-grandchildren"]?.[0]?.name ?? section.name;
}

function selectPoint(point: CourseNode) {
  selectedNodeKey.value = point.name;
}

function focusCurrentTrack() {
  const chapter = chapterNodes.value.find((item) => item.name === currentChapter.value?.name);
  if (!chapter) return;
  activeChapterKey.value = chapter.name;

  const section = (chapter.grandchildren ?? []).find((item) => item.name === currentSection.value?.name);
  if (section) {
    activeSectionKey.value = section.name;
  }

  const point = (section?.["great-grandchildren"] ?? []).find((item) => item.name === currentPoint.value?.name);
  selectedNodeKey.value = point?.name ?? section?.name ?? chapter.name;
}

function resetSelection() {
  collapseToCourse();
}

function handleGraphNodeClick(name: string) {
  const chapter = chapterNodes.value.find((item) => item.name === name);
  if (chapter) {
    selectChapter(chapter);
    return;
  }

  const section = allSections.value.find((item) => item.name === name);
  if (section) {
    const parentChapter = chapterNodes.value.find((chapterItem) => (chapterItem.grandchildren ?? []).some((item) => item.name === name));
    if (parentChapter) {
      activeChapterKey.value = parentChapter.name;
    }
    selectSection(section);
    return;
  }

  const point = allPoints.value.find((item) => item.name === name);
  if (point) {
    const parentChapter = chapterNodes.value.find((chapterItem) =>
        (chapterItem.grandchildren ?? []).some((sectionItem) =>
            (sectionItem["great-grandchildren"] ?? []).some((pointItem) => pointItem.name === name),
        ),
    );
    if (parentChapter) {
      activeChapterKey.value = parentChapter.name;
      const parentSection = (parentChapter.grandchildren ?? []).find((sectionItem) =>
          (sectionItem["great-grandchildren"] ?? []).some((pointItem) => pointItem.name === name),
      );
      if (parentSection) {
        activeSectionKey.value = parentSection.name;
      }
    }
    selectPoint(point);
    return;
  }

  selectedNodeKey.value = name;
}

function collapseToCourse() {
  activeChapterKey.value = "";
  activeSectionKey.value = "";
  selectedNodeKey.value = graph.value?.name ?? "";
}

function collapseToChapter() {
  if (!activeChapter.value) {
    collapseToCourse();
    return;
  }
  activeSectionKey.value = "";
  selectedNodeKey.value = activeChapter.value.name;
}

function renderGraphChart() {
  if (!graphChartRef.value || !graphVisualization.value) return;

  graphChart ??= init(graphChartRef.value);
  const rawNodes = graphVisualization.value.mocKgNodeDtoList ?? [];
  const rawLinks = graphVisualization.value.mocKgRelationDtoList ?? [];
  const selectedName = selectedNode.value?.name;
  const currentNames = new Set([currentChapter.value?.name, currentSection.value?.name, currentPoint.value?.name].filter(Boolean));
  const visibleNames = getProgressiveVisibleNodeNames();

  const filteredNodes = rawNodes.filter((node) => visibleNames.has(node.nodeName));
  const visibleIds = new Set(filteredNodes.map((node) => String(node.id)));
  const filteredLinks = rawLinks.filter(
      (item) => visibleIds.has(String(item.fromNodeId)) && visibleIds.has(String(item.toNodeId)),
  );

  graphChart.setOption({
    tooltip: {
      formatter: (params: { dataType?: string; data?: { name?: string; value?: string } }) => {
        if (params.dataType !== "node") return "";
        return `<strong>${params.data?.name ?? ""}</strong><br/>${params.data?.value ?? "暂无说明"}`;
      },
    },
    animationDuration: 300,
    animationDurationUpdate: 240,
    series: [
      {
        type: "graph",
        layout: "force",
        roam: true,
        draggable: true,
        force: {
          repulsion: 210,
          edgeLength: 95,
          gravity: 0.08,
          friction: 0.08,
        },
        label: {
          show: true,
          position: "right",
          fontSize: 11,
          color: "#334155",
          formatter: "{b}",
        },
        lineStyle: {
          color: "rgba(148, 163, 184, 0.4)",
          width: 1.2,
          curveness: 0.08,
        },
        emphasis: {
          focus: "adjacency",
          scale: true,
          lineStyle: {
            width: 2,
            color: "#2563eb",
          },
        },
        data: filteredNodes.map((node) => {
          const isSelected = node.nodeName === selectedName;
          const isCurrent = currentNames.has(node.nodeName);
          const isDone = String(node.flag ?? 0) === "1";
          const level = Number(node.level ?? 0);
          return {
            id: String(node.id),
            name: node.nodeName,
            value: node.description || "暂无说明",
            symbolSize: Math.max(22, 60 - level * 6),
            itemStyle: {
              color: isSelected ? "#2563eb" : isDone ? "#dbeafe" : "#ffffff",
              borderColor: isCurrent ? "#10b981" : isSelected ? "#2563eb" : "#94a3b8",
              borderWidth: isCurrent ? 4 : 2,
              shadowBlur: isSelected || isCurrent ? 18 : 8,
              shadowColor: isSelected ? "rgba(37, 99, 235, 0.22)" : "rgba(15, 23, 42, 0.08)",
            },
            label: {
              show: true,
            },
          };
        }),
        links: filteredLinks.map((item) => ({
          source: String(item.fromNodeId),
          target: String(item.toNodeId),
        })),
      },
    ],
  });

  graphChart.off("click");
  graphChart.on("click", (params: any) => {
    if (params.dataType === "node" && params.data?.name) {
      handleGraphNodeClick(params.data.name);
    }
  });

  graphChart.resize();
}

function getProgressiveVisibleNodeNames() {
  const names = new Set<string>();
  const rootName = graph.value?.name;
  if (rootName) {
    names.add(rootName);
  }

  const selectedChapter = activeChapter.value;
  const selectedSectionNode = activeSection.value;

  for (const chapter of chapterNodes.value) {
    names.add(chapter.name);
  }

  if (selectedChapter) {
    names.add(selectedChapter.name);
    for (const section of selectedChapter.grandchildren ?? []) {
      names.add(section.name);
    }
  }

  if (selectedSectionNode) {
    names.add(selectedSectionNode.name);
    for (const point of selectedSectionNode["great-grandchildren"] ?? []) {
      names.add(point.name);
    }
  }

  return names;
}

function handleResize() {
  graphChart?.resize();
}

function safeRenderGraph() {
  try {
    renderGraphChart();
  } catch (err) {
    console.error("HomeView graph render failed:", err);
    error.value = err instanceof Error ? err.message : "首页知识图谱渲染失败";
  }
}

function findCurrentNodes(graphData: { children?: CourseNode[] }) {
  let foundChapter: CurrentNodeInfo | null = null;
  let foundSection: CurrentNodeInfo | null = null;
  let foundPoint: CurrentNodeInfo | null = null;
  const children = graphData.children ?? [];

  for (let i = 0; i < children.length; i += 1) {
    const chapter = children[i];
    if (!foundChapter && chapter.flag === "0") {
      foundChapter = {name: chapter.name, index: i, total: children.length, completed: i};
    }

    const sections = chapter.grandchildren ?? [];
    for (let j = 0; j < sections.length; j += 1) {
      const section = sections[j];
      if (!foundSection && section.flag === "0" && (!foundChapter || foundChapter.index === i)) {
        foundSection = {name: section.name, index: j, total: sections.length, completed: j};
      }

      const points = section["great-grandchildren"] ?? [];
      for (let k = 0; k < points.length; k += 1) {
        const point = points[k];
        if (!foundPoint && point.flag === "0" && (!foundSection || foundSection.index === j)) {
          foundPoint = {name: point.name, index: k, total: points.length, completed: k};
          break;
        }
      }

      if (foundPoint) break;
    }

    if (foundPoint) break;
  }

  if (!foundChapter && children.length) {
    foundChapter = {name: children[0].name, index: 0, total: children.length, completed: 0};
  }

  if (!foundSection && foundChapter) {
    const chapter = children[foundChapter.index];
    const firstSection = chapter?.grandchildren?.[0];
    if (firstSection) {
      foundSection = {name: firstSection.name, index: 0, total: chapter.grandchildren?.length ?? 0, completed: 0};
    }
  }

  if (!foundPoint && foundSection && foundChapter) {
    const chapter = children[foundChapter.index];
    const section = chapter?.grandchildren?.[foundSection.index];
    const firstPoint = section?.["great-grandchildren"]?.[0];
    if (firstPoint) {
      foundPoint = {name: firstPoint.name, index: 0, total: section["great-grandchildren"]?.length ?? 0, completed: 0};
    }
  }

  return {currentChapter: foundChapter, currentSection: foundSection, currentPoint: foundPoint};
}

async function loadHome() {
  loading.value = true;
  error.value = "";
  try {
    const [knowledgeGraph, visualGraph, learningProgress] = await Promise.all([
      fetchKnowledgeGraph(),
      fetchGraphVisualization(),
      fetchLearningProgress(),
    ]);

    graph.value = knowledgeGraph;
    graphVisualization.value = visualGraph;
    progress.value = learningProgress;

    const currentNodes = findCurrentNodes(knowledgeGraph);
    currentChapter.value = currentNodes.currentChapter;
    currentSection.value = currentNodes.currentSection;
    currentPoint.value = currentNodes.currentPoint;

    focusCurrentTrack();
    if (!selectedNodeKey.value) {
      resetSelection();
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "学习首页加载失败";
  } finally {
    loading.value = false;
    await nextTick();
    safeRenderGraph();
  }
}

watch([selectedNodeKey, activeChapterKey, activeSectionKey], async () => {
  await nextTick();
  safeRenderGraph();
});

onMounted(async () => {
  await loadHome();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  graphChart?.dispose();
  graphChart = null;
});
</script>
