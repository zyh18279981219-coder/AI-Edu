<template>
  <div class="home-shell">
    <PageHero
        eyebrow="Learning Hub"
        :title="$t('student.home.learningHub')"
        :description="$t('student.home.learningHubDescription')"
        :badges="heroBadges"
        tone="learning"
    >
      <template #actions>
        <RouterLink class="primary-link" :to="continueLearningRoute">{{ $t('student.home.continueLearning') }}</RouterLink>
        <RouterLink class="ghost-btn" to="/learning">{{ $t('student.home.viewLearningPlan') }}</RouterLink>
      </template>
    </PageHero>

    <section v-if="error" class="state-card error-state">
      <h2>{{ $t('student.home.loadingError') }}</h2>
      <p>{{ error }}</p>
    </section>

    <template v-else>
      <section class="metric-grid home-metric-grid">
        <MetricStatCard
            :label="$t('student.home.chapterProgress')"
            :value="formatPercent(progress?.chapters.progress)"
            :description="$t('student.home.chapterProgressDescription',{completed:progress?.chapters.completed??0,total:progress?.chapters.total??0})"
            tone="brand"
        />
        <MetricStatCard
            :label="$t('student.home.sectionProgress')"
            :value="formatPercent(progress?.sections.progress)"
            :description="$t('student.home.sectionProgressDescription',{completed:progress?.sections.completed??0,total:progress?.sections.total??0})"
            tone="success"
        />
        <MetricStatCard
            :label="$t('student.home.pointProgress')"
            :value="formatPercent(progress?.points.progress)"
            :description="$t('student.home.pointProgressDescription',{completed:progress?.points.completed??0,total:progress?.points.total??0})"
            tone="warning"
        />
        <MetricStatCard
            :label="$t('student.home.graphStats')"
            :value="graphStats.totalNodes"
            :description="$t('student.home.knowledgeGraph',{totalRelations:graphStats.totalRelations,leafNodes:graphStats.leafNodes})"
        />
      </section>

      <section class="home-layout">
        <article class="card-panel home-graph-panel">
          <div class="section-head home-head">
            <div>
              <h2>{{$t('student.home.knowledgeGraph')}}</h2>
              <span class="muted">{{$t('student.home.knowledgeGraphDescription')}}</span>
            </div>
            <div class="home-head-actions">
              <button type="button" class="ghost-btn" @click="focusCurrentTrack">{{ $t('student.home.focusCurrentTrack') }}</button>
              <button type="button" class="ghost-btn" @click="resetSelection">{{$t('student.home.resetSelection')}}</button>
            </div>
          </div>

          <div v-if="loading" class="state-card">{{$t('student.home.loadingLearningData')}}</div>
          <template v-else>
            <div class="home-root-card">
              <div>
                <div class="home-root-kicker">{{$t('student.home.courseOverview')}}</div>
                <h3>{{ graph?.name || $t('student.home.currentCourse') }}</h3>
                <p>{{ selectedNodeDescription || $t('student.home.selectedNodeDescription') }}</p>
              </div>
              <div class="home-root-stats">
                <span class="info-pill">{{$t('student.home.chapter') }} {{chapterNodes.length }}</span>
                <span class="info-pill">{{$t('student.home.section')}} {{ progress?.sections.total ?? 0 }}</span>
                <span class="info-pill">{{$t('student.home.point')}} {{ progress?.points.total ?? 0 }}</span>
              </div>
            </div>

            <div class="home-visual-block">
              <div class="home-level-head">
                <div>
                  <h3>{{$t('student.home.knowledgeGraphView')}}</h3>
                  <span class="muted">{{$t('student.home.knowledgeGraphViewDescription')}}</span>
                </div>
                <div class="home-head-actions">
                  <button type="button" class="ghost-btn" @click="collapseToCourse">{{$t('student.home.collapseToCourse')}}</button>
                  <button type="button" class="ghost-btn" @click="collapseToChapter" :disabled="!activeChapter">
                    {{$t('student.home.collapseToChapter')}}
                  </button>
                </div>
              </div>
              <div class="home-graph-breadcrumb">
                <button type="button" class="home-crumb" :class="{ active: !activeChapterKey }"
                        @click="collapseToCourse">
                  {{$t('student.home.courseOverview')}}
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
                <h3>{{$t('student.home.chapter')}}</h3>
                <span class="muted">{{$t('student.home.numberOfChapters',chapterNodes.length,{named:{number:chapterNodes.length} })}}</span>
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
                  <span class="home-node-meta">{{ nodeMeta(chapter, $t('student.home.chapter')) }}</span>
                </button>
              </div>
            </div>

            <div class="home-level-block">
              <div class="home-level-head">
                <h3>{{$t('student.home.section')}}</h3>
                <span class="muted">{{$t('student.home.numberOfSections',activeSections.length,{named:{number:activeSections.length} })}}</span>
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
                  <span class="home-node-meta">{{ nodeMeta(section, $t('student.home.section')) }}</span>
                </button>
                <div v-if="!activeSections.length" class="list-card">{{$t('student.home.noSectionsData')}}</div>
              </div>
            </div>

            <div class="home-level-block">
              <div class="home-level-head">
                <h3>{{$t('student.home.point')}}</h3>
                <span class="muted">{{$t('student.home.numberOfPoints',activePoints.length,{named:{number:activePoints.length} })}}</span>
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
                    <div class="home-node-meta">{{ nodeMeta(point, $t('student.home.point')) }}</div>
                  </div>
                  <span class="pill" :class="nodeFlag(point) === '1' ? 'mastery-high' : 'mastery-mid'">
                    {{ nodeFlag(point) === "1" ? $t('student.home.complete') : $t('student.home.inProgress') }}
                  </span>
                </button>
                <div v-if="!activePoints.length" class="list-card">{{$t('student.home.noPointData')}}</div>
              </div>
            </div>
          </template>
        </article>

        <aside class="home-sidebar">
          <article class="card-panel home-progress-card">
            <div class="section-head">
              <h2>{{ $t('student.home.currentLearningPositioning') }}</h2>
              <span class="muted">{{ $t('student.home.incompleteNodePositioning') }}</span>
            </div>
            <div class="home-progress-stack">
              <div class="home-progress-item">
                <div class="home-progress-top">
                  <strong>{{ $t('student.home.currentChapter') }}</strong>
                  <span>{{ currentChapter?.name || $t('student.home.none') }}</span>
                </div>
                <div class="progress-line"><span :style="{ width: `${currentChapterPercent}%` }"></span></div>
                <small>{{ currentChapterProgressText }}</small>
              </div>
              <div class="home-progress-item">
                <div class="home-progress-top">
                  <strong>{{$t('student.home.currentSection')}}</strong>
                  <span>{{ currentSection?.name || $t('student.home.none') }}</span>
                </div>
                <div class="progress-line"><span :style="{ width: `${currentSectionPercent}%` }"></span></div>
                <small>{{ currentSectionProgressText }}</small>
              </div>
              <div class="home-progress-item">
                <div class="home-progress-top">
                  <strong>{{$t('student.home.currentPoint')}}</strong>
                  <span>{{ currentPoint?.name || $t('student.home.none') }}</span>
                </div>
                <div class="progress-line"><span :style="{ width: `${currentPointPercent}%` }"></span></div>
                <small>{{ currentPointProgressText }}</small>
              </div>
            </div>
          </article>

          <article class="card-panel home-detail-card">
            <div class="section-head">
              <h2>{{ $t('student.home.pointDetail') }}</h2>
              <span class="muted">{{ selectedNodeLabel }}</span>
            </div>
            <div class="home-detail-body">
              <h3>{{ selectedNodeTitle }}</h3>
              <p>{{ selectedNodeDescription || $t('student.home.none') }}</p>
              <div class="home-detail-meta">
                <span class="meta-chip">{{$t('student.home.learningStatus',{status:selectedNodeFlagText})}}</span>
                <span class="meta-chip">{{$t('student.home.averageMastery',{value:selectedNodeStats.avgMastery})}}</span>
                <span class="meta-chip">{{$t('student.home.averageCompletion',{value:selectedNodeStats.avgCompletion})}}</span>
                <span class="meta-chip">{{$t('student.home.averageStudyDuration',{minutes:selectedNodeStats.avgStudyDuration})}}</span>
              </div>
            </div>
          </article>

          <article class="card-panel home-action-card">
            <div class="section-head">
              <h2>{{ $t('student.home.nextStep') }}</h2>
            </div>
            <div class="stack-list">
              <div class="list-card">
                <div class="list-title">{{ $t('student.home.prioritizeCurrentPoint') }}</div>
                <div class="list-meta">{{ currentPoint?.name || $t('student.home.noPoint') }}</div>
                <RouterLink class="primary-link home-action-link" :to="continueLearningRoute">{{$t('student.home.enterCourseContent')}}</RouterLink>
              </div>
              <div class="list-card">
                <div class="list-title">{{ $t('student.home.viewLearningPlan') }}</div>
                <div class="list-meta">{{$t('student.home.viewLearningPlanDescription')}}</div>
                <RouterLink class="ghost-btn home-action-link" to="/learning">{{$t('student.home.openMyLearning')}}</RouterLink>
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
import {GraphVisualizationResponse, LearningProgressResponse, GraphVisualizationNode} from "../../types/student";
import {fetchLearningProgress, fetchGraphVisualization} from '../../api/student';
import {type CourseNode,type CurrentNodeInfo} from "../../types/knowledgeGraph";
import {fetchKnowledgeGraph} from "../../api/knowledgeGraph";
import i18n from "../../locale/index";

const {t}=i18n.global

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
  `${t('student.home.chapter')} ${progress.value?.chapters.total ?? 0}`,
  `${t('student.home.current')} ${currentPoint.value?.name ?? "未定位"}`,
  `${t("student.home.relationship")} ${graphStats.value.totalRelations}`,
]);

const selectedNodeTitle = computed(() => selectedNode.value?.name || graph.value?.name || "当前课程");
const selectedNodeDescription = computed(() => {
  if (!selectedNode.value) return "";
  return graphNodeMap.value.get(selectedNode.value.name)?.description || selectedNode.value.description || "";
});
const selectedNodeLabel = computed(() => {
  if (!selectedNode.value) return "课程节点";
  if (allPoints.value.some((item) => item.name === selectedNode.value?.name)) return t('student.home.point');
  if (allSections.value.some((item) => item.name === selectedNode.value?.name)) return t('studetn.home.section');
  if (chapterNodes.value.some((item) => item.name === selectedNode.value?.name)) return t('student.home.chapter');
  return "课程节点";
});
const selectedNodeFlagText = computed(() => (nodeFlag(selectedNode.value) === "1" ? t('student.home.complete') : t('student.home.inProgress')));
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

const currentChapterProgressText = computed(() => currentText(currentChapter.value, t('student.home.chapter')));
const currentSectionProgressText = computed(() => currentText(currentSection.value, t('student.home.section')));
const currentPointProgressText = computed(() => currentText(currentPoint.value, t('student.home.point')));

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
  return `${label} · ${nodeFlag(node) === "1" ? t('student.home.complete') : t('student.home.continue')}`;
}

function computePercent(node: CurrentNodeInfo | null) {
  if (!node || !node.total) return 0;
  return Number(((node.completed / node.total) * 100).toFixed(1));
}

function currentText(node: CurrentNodeInfo | null, label: string) {
  if(!node) return t('student.home.noLearningPosition',{label:label});
  return t('student.home.completeLearningPosition',{label:label,current:node.index+1,total:node.total,completed:node.completed})
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
