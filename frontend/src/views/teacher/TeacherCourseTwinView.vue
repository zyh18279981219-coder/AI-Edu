<template>
  <div class="teacher-course-twin-shell">
    <section class="hero-panel app-hero app-hero--teacher">
      <div>
        <p class="eyebrow">课程数字孪生</p>
        <h1>课程底座建设台</h1>
        <p class="hero-desc">教师录入课程大纲后生成初始知识图谱，系统按叶子知识点绑定资源候选，审核通过后发布给学生端和诊断链路使用。</p>
      </div>
      <div class="course-twin-hero-actions">
        <button class="ghost-btn" type="button" :disabled="loading" @click="loadCourses">刷新</button>
        <button class="primary-btn" type="button" :disabled="!activeCourseId || loading" @click="publishCurrentCourse">
          发布课程底座
        </button>
      </div>
    </section>

    <section v-if="notice" class="card-panel state-card">{{ notice }}</section>
    <section v-if="error" class="card-panel state-card error">{{ error }}</section>

    <section class="course-publish-flow card-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Publish Boundary</p>
          <h3>课程底座发布前检查</h3>
        </div>
        <span class="status-pill" :class="`status-${coursePublishState.code}`">{{ coursePublishState.label }}</span>
      </div>
      <div class="course-publish-steps">
        <article
          v-for="step in coursePublishSteps"
          :key="step.key"
          class="course-publish-step"
          :class="`is-${step.state}`"
        >
          <span>{{ step.index }}</span>
          <div>
            <strong>{{ step.title }}</strong>
            <p>{{ step.description }}</p>
          </div>
        </article>
      </div>
      <div class="course-publish-boundary">
        <strong>生效边界</strong>
        <span>草稿和待审核内容学生不可见；资源、测验和能力映射经过教师确认并发布后，才进入学生端、诊断链路和个性化路径。</span>
      </div>
    </section>

    <section class="course-twin-grid">
      <article ref="courseBuilderPanelRef" class="card-panel course-twin-builder">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Initial Graph</p>
            <h3>教师生成初始知识图谱</h3>
          </div>
          <span class="status-pill">{{ generatedSummary?.lifecycle_status || selectedSummary?.lifecycle_status || "draft" }}</span>
        </div>

        <div class="form-grid">
          <label>
            <span>课程 ID</span>
            <input v-model.trim="form.course_id" class="input" placeholder="course_big_data" />
          </label>
          <label>
            <span>课程名称</span>
            <input v-model.trim="form.course_name" class="input" placeholder="大数据分析" />
          </label>
        </div>

        <div class="tree-editor">
          <div class="tree-editor-head">
            <div>
              <span class="field-label">课程结构</span>
              <p>按章节、小节、知识点维护课程树；资源候选只会绑定到叶子知识点。</p>
            </div>
            <button class="tree-add-root" type="button" :disabled="loading" @click="addChapter">
              <Plus />
              <span>添加章节</span>
            </button>
          </div>

          <div class="course-tree-form">
            <div v-for="(chapter, chapterIndex) in treeForm" :key="chapter.id" class="tree-node tree-node--chapter">
              <div class="tree-row tree-row--chapter">
                <button class="tree-toggle" type="button" :aria-label="chapter.collapsed ? '展开章节' : '收起章节'" @click="chapter.collapsed = !chapter.collapsed">
                  <ArrowRight v-if="chapter.collapsed" />
                  <ArrowDown v-else />
                </button>
                <span class="tree-type tree-type--chapter">章</span>
                <span class="tree-index">第 {{ chapterIndex + 1 }} 章</span>
                <input v-model.trim="chapter.name" class="tree-input" placeholder="输入章节名称，如 数据采集" />
                <div class="tree-actions">
                  <button class="tree-icon-btn" type="button" title="添加小节" aria-label="添加小节" :disabled="loading" @click="addSection(chapter)">
                    <Plus />
                  </button>
                  <button class="tree-icon-btn danger" type="button" title="删除章节" aria-label="删除章节" :disabled="loading || treeForm.length <= 1" @click="removeChapter(chapterIndex)">
                    <Delete />
                  </button>
                </div>
              </div>

              <div v-if="!chapter.collapsed" class="tree-children">
                <div v-for="(section, sectionIndex) in chapter.children" :key="section.id" class="tree-node tree-node--section">
                  <div class="tree-row tree-row--section">
                    <button class="tree-toggle" type="button" :aria-label="section.collapsed ? '展开小节' : '收起小节'" @click="section.collapsed = !section.collapsed">
                      <ArrowRight v-if="section.collapsed" />
                      <ArrowDown v-else />
                    </button>
                    <span class="tree-type tree-type--section">节</span>
                    <span class="tree-index">{{ chapterIndex + 1 }}.{{ sectionIndex + 1 }}</span>
                    <input v-model.trim="section.name" class="tree-input" placeholder="输入小节名称，如 数据采集概述" />
                    <div class="tree-actions">
                      <button class="tree-icon-btn" type="button" title="添加知识点" aria-label="添加知识点" :disabled="loading" @click="addKnowledgePoint(section)">
                        <Plus />
                      </button>
                      <button class="tree-icon-btn danger" type="button" title="删除小节" aria-label="删除小节" :disabled="loading || chapter.children.length <= 1" @click="removeSection(chapter, sectionIndex)">
                        <Delete />
                      </button>
                    </div>
                  </div>

                  <div v-if="!section.collapsed" class="tree-leaves">
                    <div v-for="(point, pointIndex) in section.children" :key="point.id" class="tree-node tree-node--leaf">
                      <span class="tree-leaf-rail"></span>
                      <span class="tree-type tree-type--point">点</span>
                      <span class="tree-index">{{ chapterIndex + 1 }}.{{ sectionIndex + 1 }}.{{ pointIndex + 1 }}</span>
                      <input v-model.trim="point.name" class="tree-input" placeholder="输入知识点名称，如 Flume 基础" />
                      <div class="tree-actions">
                        <button class="tree-icon-btn danger" type="button" title="删除知识点" aria-label="删除知识点" :disabled="loading || section.children.length <= 1" @click="removeKnowledgePoint(section, pointIndex)">
                          <Delete />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="builder-options">
          <label class="checkbox-row">
            <input v-model="form.bind_resource_candidates" type="checkbox" />
            <span>生成后同时绑定资源候选</span>
          </label>
          <label class="compact-field">
            <span>每个叶子知识点</span>
            <input v-model.number="form.max_resources_per_leaf" class="input" type="number" min="1" max="3" />
          </label>
        </div>

        <div class="action-row">
          <button class="primary-btn" type="button" :disabled="loading || !canGenerate" @click="generateInitialGraph">
            {{ loading ? "处理中..." : "生成并保存图谱" }}
          </button>
          <button class="ghost-btn" type="button" :disabled="loading || !activeCourseId" @click="bindResources">
            绑定资源候选
          </button>
        </div>
      </article>

      <article class="card-panel course-twin-side">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Course Base</p>
            <h3>课程状态</h3>
          </div>
        </div>
        <div class="course-list">
          <button
            v-for="course in courses"
            :key="course.course_id"
            type="button"
            class="course-row"
            :class="{ active: course.course_id === activeCourseId }"
            @click="selectCourse(course.course_id)"
          >
            <span>
              <strong>{{ course.course_name }}</strong>
              <small>{{ course.course_id }}</small>
            </span>
            <em>{{ course.lifecycle_status }}</em>
          </button>
          <div v-if="!courses.length" class="muted">暂无课程底座</div>
        </div>

        <div v-if="activeSummary" class="summary-grid">
          <div><span>节点</span><strong>{{ activeSummary.node_count }}</strong></div>
          <div><span>叶子</span><strong>{{ activeSummary.leaf_node_count ?? 0 }}</strong></div>
          <div><span>资源</span><strong>{{ activeSummary.resource_count }}</strong></div>
          <div><span>启用</span><strong>{{ activeSummary.enabled_resource_count ?? 0 }}</strong></div>
        </div>
      </article>
    </section>

    <section class="course-twin-grid lower">
      <article class="card-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Graph Preview</p>
            <h3>知识图谱预览</h3>
          </div>
        </div>
        <div v-if="flatGraphNodes.length" class="graph-tree">
          <div
            v-for="item in flatGraphNodes"
            :key="item.key"
            class="graph-node-line"
            :style="{ marginLeft: `${item.depth * 14}px` }"
          >
            <strong>{{ item.name }}</strong>
            <span v-if="item.resourceCount">{{ item.resourceCount }} 个资源</span>
          </div>
        </div>
        <div v-else class="muted">生成或选择课程后显示图谱结构</div>
      </article>

      <article class="card-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Resource Review</p>
            <h3>资源绑定审核</h3>
          </div>
          <button class="ghost-btn small" type="button" :disabled="!activeCourseId || loading" @click="refreshResources">
            刷新资源
          </button>
        </div>
        <div class="resource-review-toolbar">
          <div class="resource-filter-tabs" role="tablist" aria-label="资源审核筛选">
            <button
              v-for="tab in resourceFilterTabs"
              :key="tab.key"
              type="button"
              class="resource-filter-tab"
              :class="{ active: resourceFilter === tab.key }"
              @click="resourceFilter = tab.key"
            >
              {{ tab.label }} <strong>{{ tab.count }}</strong>
            </button>
          </div>
          <button
            class="ghost-btn small"
            type="button"
            :disabled="loading || !pendingResourceReviewCount"
            @click="batchEnablePendingResources"
          >
            批量启用待审核
          </button>
        </div>
        <div class="resource-review-list">
          <div v-for="resource in filteredResources" :key="resource.resource_id" class="resource-review-row">
            <div>
              <strong>{{ resource.node_name || resource.node_id }}</strong>
              <a :href="resource.resource_path" target="_blank" rel="noreferrer">{{ displayResource(resource.resource_path) }}</a>
              <span>{{ resourceSourceText(resource.resource_source) }} · {{ reviewStatusText(resource.review_status) }} · {{ resourceQualityText(resource.quality_status) }}</span>
            </div>
            <div class="resource-actions">
              <button class="ghost-btn small" type="button" :disabled="loading" @click="setResourceEnabled(resource, true)">启用</button>
              <button class="ghost-btn small danger" type="button" :disabled="loading" @click="setResourceEnabled(resource, false)">禁用</button>
            </div>
          </div>
          <div v-if="!resources.length" class="muted">暂无资源候选</div>
          <div v-else-if="!filteredResources.length" class="muted">当前筛选下暂无资源</div>
        </div>
      </article>
    </section>

    <section ref="quizDefinitionPanelRef" class="course-quiz-panel card-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Quiz Definition</p>
          <h3>节点测验定义</h3>
        </div>
        <button class="ghost-btn small" type="button" :disabled="!activeCourseId || !quizForm.node_id || loading" @click="loadQuizDefinitions">
          刷新测验
        </button>
      </div>

      <div class="quiz-definition-layout">
        <div class="quiz-definition-editor">
          <div class="form-grid">
            <label>
              <span>课程节点</span>
              <select v-model="quizForm.node_id" class="input" :disabled="!leafNodeOptions.length" @change="handleQuizNodeChange">
                <option v-for="node in leafNodeOptions" :key="node.node_id" :value="node.node_id">
                  {{ node.pathText }}
                </option>
              </select>
            </label>
            <label>
              <span>测验标题</span>
              <input v-model.trim="quizForm.title" class="input" placeholder="如：Kafka 数据接入小测" />
            </label>
          </div>

          <div class="quiz-question-list">
            <div v-for="(question, index) in quizForm.questions" :key="question.id" class="quiz-question-row">
              <div class="quiz-question-head">
                <strong>题目 {{ index + 1 }}</strong>
                <button class="tree-icon-btn danger" type="button" :disabled="quizForm.questions.length <= 1 || loading" @click="removeQuizQuestion(index)">
                  <Delete />
                </button>
              </div>
              <textarea
                v-model.trim="question.question"
                class="input quiz-question-textarea"
                rows="5"
                placeholder="题干与选项，例如：&#10;以下关于 Kafka Topic 的说法正确的是？&#10;A. 只能有一个分区&#10;B. 可以按分区并行消费&#10;C. 不能持久化消息&#10;D. 与消费者无关"
              ></textarea>
              <div class="quiz-answer-row">
                <label>
                  <span>正确答案</span>
                  <select v-model="question.correct" class="input">
                    <option value="a">A</option>
                    <option value="b">B</option>
                    <option value="c">C</option>
                    <option value="d">D</option>
                  </select>
                </label>
              </div>
            </div>
          </div>

          <div class="action-row">
            <button class="ghost-btn small" type="button" :disabled="loading" @click="addQuizQuestion">添加题目</button>
            <button class="primary-btn" type="button" :disabled="loading || !canSaveQuizDefinition" @click="saveCurrentQuizDefinition('draft')">
              保存草稿
            </button>
            <button class="primary-btn" type="button" :disabled="loading || !canSaveQuizDefinition" @click="saveCurrentQuizDefinition('published')">
              保存并发布
            </button>
          </div>
        </div>

        <aside class="quiz-definition-list">
          <div v-for="definition in quizDefinitions" :key="definition.definition_id" class="quiz-definition-card">
            <div>
              <strong>{{ definition.title }}</strong>
              <span>{{ quizDefinitionStatusText(definition.status) }} · {{ definition.questions.length }} 题 · v{{ definition.version_no ?? 1 }}</span>
              <small v-if="definition.published_at">发布于 {{ definition.published_at }}</small>
            </div>
            <button class="ghost-btn small" type="button" :disabled="loading" @click="loadQuizDefinitionIntoForm(definition)">
              编辑
            </button>
            <button
              class="ghost-btn small"
              type="button"
              :disabled="loading || definition.status === 'published'"
              @click="publishExistingQuizDefinition(definition.definition_id)"
            >
              发布
            </button>
          </div>
          <div v-if="!quizDefinitions.length" class="muted">选择叶子知识点后，可保存并发布该节点的正式小测。</div>
        </aside>
      </div>
    </section>

    <section class="course-runtime-panel card-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Runtime Evaluation</p>
          <h3>课程运行评估</h3>
        </div>
        <button class="ghost-btn small" type="button" :disabled="!activeCourseId || loading" @click="refreshRuntimeEvaluation">
          刷新评估
        </button>
      </div>

      <div v-if="runtimeEvaluation" class="runtime-layout">
        <div class="runtime-health">
          <span>课程健康分</span>
          <strong>{{ formatScore(runtimeMetrics.course_health_score) }}</strong>
          <em>{{ healthLevel(runtimeMetrics.course_health_score) }}</em>
          <small>窗口 {{ runtimeEvaluation.window_days }} 天 · 有效作答阈值 {{ runtimeEvaluation.required_participant_count ?? runtimeEvaluation.min_quiz_attempts }}</small>
        </div>

        <div class="runtime-score-grid runtime-score-grid--five">
          <div v-for="item in runtimeScoreCards" :key="item.label" class="runtime-score-card">
            <span>{{ item.label }}</span>
            <strong>{{ formatScore(item.value) }}</strong>
            <small>{{ item.hint }}</small>
          </div>
          <div class="runtime-score-card">
            <span>资源覆盖</span>
            <strong>{{ formatPercent(runtimeMetrics.resource_coverage_rate) }}</strong>
            <small>有效资源覆盖率</small>
          </div>
          <div class="runtime-score-card">
            <span>测评覆盖</span>
            <strong>{{ formatPercent(runtimeMetrics.assessment_coverage_rate) }}</strong>
            <small>小测与作业证据覆盖</small>
          </div>
          <div class="runtime-score-card">
            <span>能力支撑</span>
            <strong>{{ formatPercent(runtimeMetrics.ability_support_rate) }}</strong>
            <small>已确认能力映射支撑率</small>
          </div>
        </div>
      </div>

      <div v-if="runtimeEvaluation" class="runtime-columns">
        <div class="runtime-block">
          <h4>教师行动项</h4>
          <div v-for="item in runtimeActionItems" :key="`${item.type}-${item.priority}`" class="runtime-row">
            <strong>{{ item.title }}</strong>
            <span>{{ priorityText(item.priority) }}优先级 · {{ item.count }} 项</span>
            <button
              v-if="runtimeActionButtonText(item.type)"
              class="ghost-btn tiny"
              type="button"
              :disabled="loading"
              @click="handleRuntimeActionItem(item.type)"
            >
              {{ runtimeActionButtonText(item.type) }}
            </button>
          </div>
          <div v-if="!runtimeActionItems.length" class="muted">暂无行动项</div>
        </div>

        <div class="runtime-block">
          <h4>资源与测评缺口</h4>
          <div v-for="item in runtimeResourceGaps.slice(0, 4)" :key="`resource-${item.node_id || runtimeNodeTitle(item)}`" class="runtime-row">
            <strong>{{ runtimeNodeTitle(item) }}</strong>
            <span>{{ item.reason || "资源支撑不足" }}</span>
            <button
              class="ghost-btn tiny"
              type="button"
              :disabled="loading"
              @click="prepareResourceGapBinding(item)"
            >
              补资源
            </button>
          </div>
          <div v-for="item in runtimeAssessmentGaps.slice(0, 3)" :key="`assessment-${item.node_id || runtimeNodeTitle(item)}`" class="runtime-row">
            <strong>{{ runtimeNodeTitle(item) }}</strong>
            <span>{{ item.reason || "测评证据不足" }}</span>
            <button
              class="ghost-btn tiny"
              type="button"
              :disabled="loading || !item.node_id"
              @click="prepareAssessmentGapQuiz(item)"
            >
              补测验
            </button>
          </div>
          <div v-if="!runtimeResourceGaps.length && !runtimeAssessmentGaps.length" class="muted">暂无明显资源或测评缺口</div>
        </div>

        <div class="runtime-block">
          <h4>运行风险</h4>
          <div v-for="item in runtimeRiskNodes.slice(0, 4)" :key="`risk-${item.node_id || runtimeNodeTitle(item)}`" class="runtime-row">
            <strong>{{ runtimeNodeTitle(item) }}</strong>
            <span>K_risk {{ formatScore(item.k_risk) }} · 掌握 {{ formatScore(item.avg_mastery) }}</span>
          </div>
          <div v-for="item in runtimeChapterRisks.slice(0, 2)" :key="`chapter-${runtimeChapterTitle(item)}`" class="runtime-row">
            <strong>{{ runtimeChapterTitle(item) }}</strong>
            <span>高风险 {{ item.high_risk_node_count ?? 0 }} / {{ item.evidence_sufficient_node_count ?? 0 }}</span>
          </div>
          <div v-if="!runtimeRiskNodes.length && !runtimeChapterRisks.length" class="muted">暂无高风险知识点或章节</div>
        </div>

        <div class="runtime-block">
          <h4>职业能力支撑</h4>
          <div v-for="item in runtimeAbilityGaps.slice(0, 5)" :key="`ability-${item.ability_id || runtimeAbilityTitle(item)}`" class="runtime-row">
            <strong>{{ runtimeAbilityTitle(item) }}</strong>
            <span>A_sup {{ formatScore(item.a_sup) }} · {{ item.reason || "能力支撑不足" }}</span>
            <button
              class="ghost-btn tiny"
              type="button"
              :disabled="loading || !item.ability_id"
              @click="prepareAbilityGapMapping(item)"
            >
              补映射
            </button>
            <button
              class="ghost-btn tiny"
              type="button"
              :disabled="loading || !item.ability_id || !sectionPlacementOptions.length"
              @click="prepareAbilityGapDraftNode(item)"
            >
              补草稿知识点
            </button>
          </div>
          <div v-if="!runtimeAbilityGaps.length" class="muted">暂无职业能力支撑缺口</div>
        </div>
      </div>

      <div v-if="runtimeEvaluation && runtimeUnavailableMetrics.length" class="runtime-evidence-note">
        <strong>数据不足项</strong>
        <span v-for="item in runtimeUnavailableMetrics" :key="item.metric">{{ item.metric }}：{{ item.reason }}</span>
      </div>
      <div v-if="!runtimeEvaluation" class="muted">选择课程后显示运行评估</div>
    </section>

    <section class="course-twin-grid lower">
      <article class="card-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Ability Mapping</p>
            <h3>职业能力映射审核</h3>
          </div>
          <div class="resource-actions">
            <button class="ghost-btn small" type="button" :disabled="!activeCourseId || loading" @click="refreshAbilityMappings">
              刷新映射
            </button>
            <button class="ghost-btn small" type="button" :disabled="!canGenerateAbilityMappingCandidates || loading" @click="generateAbilityMappingCandidates">
              生成映射候选
            </button>
            <button class="ghost-btn small" type="button" :disabled="loading || !pendingAbilityMappings.length" @click="reviewPendingAbilityMappings('confirmed')">
              批量确认待审核
            </button>
            <button class="ghost-btn small danger" type="button" :disabled="loading || !pendingAbilityMappings.length" @click="reviewPendingAbilityMappings('rejected')">
              批量驳回待审核
            </button>
          </div>
        </div>

        <div class="summary-grid ability-summary-grid">
          <div><span>岗位方向</span><strong>{{ positions.length }}</strong></div>
          <div><span>能力候选</span><strong>{{ abilities.length }}</strong></div>
          <div><span>映射关系</span><strong>{{ abilityMappings.length }}</strong></div>
          <div><span>待审核</span><strong>{{ pendingAbilityMappingCount }}</strong></div>
        </div>
        <div class="ability-review-note">
          教师确认后的能力映射才会进入正式课程底座；学生端只读取已确认映射并展示能力达成等级，不展示来源证据和审核过程。
        </div>
        <p v-if="abilityCandidateHint" class="ability-candidate-hint">{{ abilityCandidateHint }}</p>

        <div v-if="abilityGapDraftForm.visible" class="ability-config-card ability-gap-draft-card">
          <div class="draft-card-head">
            <div>
              <strong>能力缺口补知识点草稿</strong>
              <p>新增节点先保存到课程图谱草稿，并重新绑定 B 站、YouTube、CSDN 资源候选；教师审核资源和映射后再发布新版课程底座。</p>
            </div>
            <button class="ghost-btn tiny" type="button" :disabled="loading" @click="closeAbilityGapDraftForm">收起</button>
          </div>
          <div class="form-grid ability-form-grid">
            <label>
              <span>建议知识点名称</span>
              <input v-model.trim="abilityGapDraftForm.node_name" class="input" placeholder="如：实时数据接入实践" />
            </label>
            <label>
              <span>建议放置位置</span>
              <select v-model="abilityGapDraftForm.section_key" class="input" :disabled="!sectionPlacementOptions.length">
                <option v-for="section in sectionPlacementOptions" :key="section.key" :value="section.key">
                  {{ section.pathText }}
                </option>
              </select>
            </label>
          </div>
          <textarea
            v-model.trim="abilityGapDraftForm.description"
            class="input ability-import-textarea ability-mapping-reason"
            rows="3"
            placeholder="说明该知识点为什么用于补齐职业能力缺口"
          ></textarea>
          <div class="form-grid ability-form-grid">
            <label>
              <span>资源检索关键词</span>
              <input v-model.trim="abilityGapDraftForm.resource_keywords" class="input" placeholder="如：实时数据接入 Kafka Flume 教程" />
            </label>
            <label>
              <span>关联能力</span>
              <select v-model.number="abilityGapDraftForm.ability_id" class="input" :disabled="!abilities.length">
                <option :value="0">选择能力</option>
                <option v-for="ability in abilities" :key="ability.ability_id" :value="ability.ability_id">
                  {{ ability.position_name }} / {{ ability.ability_name }}
                </option>
              </select>
            </label>
          </div>
          <div class="action-row">
            <button class="primary-btn small" type="button" :disabled="loading || !canSaveAbilityGapDraftNode" @click="saveAbilityGapDraftNode">
              保存草稿节点并绑定资源候选
            </button>
          </div>
        </div>

        <div ref="abilityMappingFormRef" class="ability-config-card ability-mapping-create-card">
          <strong>补充能力映射</strong>
          <p v-if="abilityMappingRuntimeHint" class="ability-runtime-hint">{{ abilityMappingRuntimeHint }}</p>
          <div class="form-grid ability-form-grid">
            <label>
              <span>职业能力</span>
              <select v-model.number="abilityMappingForm.ability_id" class="input" :disabled="!abilities.length">
                <option :value="0">选择能力</option>
                <option v-for="ability in abilities" :key="ability.ability_id" :value="ability.ability_id">
                  {{ ability.position_name }} / {{ ability.ability_name }}
                </option>
              </select>
            </label>
            <label>
              <span>叶子知识点</span>
              <select v-model="abilityMappingForm.node_id" class="input" :disabled="!leafNodeOptions.length">
                <option value="">选择知识点</option>
                <option v-for="node in leafNodeOptions" :key="node.node_id" :value="node.node_id">
                  {{ node.pathText }}
                </option>
              </select>
            </label>
            <label>
              <span>支撑强度</span>
              <select v-model="abilityMappingForm.support_level" class="input">
                <option value="high">强支撑</option>
                <option value="medium">中支撑</option>
                <option value="low">弱支撑</option>
              </select>
            </label>
            <label>
              <span>审核状态</span>
              <select v-model="abilityMappingForm.review_status" class="input">
                <option value="draft">保存为草稿</option>
                <option value="confirmed">直接确认</option>
              </select>
            </label>
          </div>
          <textarea
            v-model.trim="abilityMappingForm.match_reason"
            class="input ability-import-textarea ability-mapping-reason"
            rows="3"
            placeholder="填写匹配依据，如岗位能力要求、课程目标或资源证据"
          ></textarea>
          <button class="primary-btn small" type="button" :disabled="loading || !canSaveAbilityMapping" @click="saveAbilityMapping">
            保存能力映射
          </button>
        </div>

        <div class="ability-mapping-list">
          <div v-for="mapping in abilityMappings" :key="mapping.mapping_id" class="ability-mapping-row">
            <div class="ability-mapping-main">
              <div class="ability-mapping-title-row">
                <strong>{{ mapping.ability_name }}</strong>
                <span class="ability-status-pill" :class="`status-${normalizedReviewStatus(mapping.review_status)}`">
                  {{ reviewStatusText(mapping.review_status) }}
                </span>
              </div>
              <div class="ability-mapping-meta-grid">
                <div>
                  <span>岗位方向</span>
                  <strong>{{ mapping.position_name || "未绑定岗位" }}</strong>
                </div>
                <div>
                  <span>叶子知识点</span>
                  <strong>{{ mapping.node_path?.join(" / ") || mapping.node_name || mapping.node_id }}</strong>
                </div>
                <div>
                  <span>支撑强度</span>
                  <strong>{{ supportLevelText(mapping.support_level) }}</strong>
                </div>
              </div>
              <p class="ability-evidence-line">
                {{ mapping.match_reason || mappingEvidenceSummary(mapping) }}
              </p>
            </div>
            <div class="resource-actions">
              <button
                class="ghost-btn small"
                type="button"
                :disabled="loading || normalizedReviewStatus(mapping.review_status) === 'confirmed'"
                @click="reviewAbilityMapping(mapping, 'confirmed')"
              >
                确认
              </button>
              <button
                class="ghost-btn small danger"
                type="button"
                :disabled="loading || normalizedReviewStatus(mapping.review_status) === 'rejected'"
                @click="reviewAbilityMapping(mapping, 'rejected')"
              >
                驳回
              </button>
            </div>
          </div>
          <div v-if="!abilityMappings.length" class="muted">暂无职业能力映射。请先导入岗位能力候选并生成映射关系。</div>
        </div>
      </article>

      <article ref="resourceReviewPanelRef" class="card-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Positions</p>
            <h3>岗位与能力候选</h3>
          </div>
        </div>
        <div class="ability-config-grid">
          <div class="ability-config-card">
            <strong>配置目标岗位</strong>
            <div class="form-grid ability-form-grid">
              <label>
                <span>岗位名称</span>
                <input v-model.trim="positionForm.position_name" class="input" placeholder="如：大数据工程师" />
              </label>
              <label>
                <span>方向类型</span>
                <select v-model="positionForm.position_type" class="input">
                  <option value="primary">主目标岗位</option>
                  <option value="related">关联岗位</option>
                </select>
              </label>
              <label>
                <span>排序</span>
                <input v-model.number="positionForm.target_rank" class="input" type="number" min="0" />
              </label>
              <label>
                <span>来源关键词</span>
                <input v-model.trim="positionForm.source_keyword" class="input" placeholder="岗位检索词或行业来源" />
              </label>
            </div>
            <button class="primary-btn small" type="button" :disabled="loading || !canSavePosition" @click="savePosition">
              保存岗位方向
            </button>
          </div>

          <div class="ability-config-card">
            <strong>导入能力候选</strong>
            <div class="form-grid ability-form-grid">
              <label>
                <span>目标岗位</span>
                <select v-model.number="abilityImportForm.position_id" class="input" :disabled="!positions.length">
                  <option :value="0">选择岗位</option>
                  <option v-for="position in positions" :key="position.position_id" :value="position.position_id">
                    {{ position.position_name }}
                  </option>
                </select>
              </label>
              <label>
                <span>默认类别</span>
                <input v-model.trim="abilityImportForm.default_category" class="input" placeholder="如：数据处理" />
              </label>
            </div>
            <textarea
              v-model.trim="abilityImportForm.raw_text"
              class="input ability-import-textarea"
              rows="5"
              placeholder="每行一个能力；也可粘贴 JSON 数组，如 [{&quot;ability_name&quot;:&quot;实时数据接入&quot;,&quot;demand_level&quot;:&quot;high&quot;}]"
            ></textarea>
            <button class="primary-btn small" type="button" :disabled="loading || !canImportAbilities" @click="importAbilities">
              导入能力候选
            </button>
          </div>
        </div>

        <div class="course-list">
          <div v-for="position in positions" :key="position.position_id" class="course-row readonly-row">
            <span>
              <strong>{{ position.position_name }}</strong>
              <small>{{ position.position_type || "position" }}</small>
            </span>
            <em>{{ position.target_rank ?? 0 }}</em>
          </div>
          <div v-if="!positions.length" class="muted">暂无岗位方向</div>
        </div>
        <div class="ability-chip-list">
          <span v-for="ability in abilities.slice(0, 12)" :key="ability.ability_id" class="ability-chip">
            {{ ability.ability_name }}
          </span>
        </div>
        <div v-if="abilities.length > 12" class="muted">另有 {{ abilities.length - 12 }} 个能力候选未展开显示</div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import { ArrowDown, ArrowRight, Delete, Plus } from "@element-plus/icons-vue";
import { useRoute } from "vue-router";
import {
  bindCourseResourceCandidates,
  fetchCourseDigitalTwin,
  fetchCourseDigitalTwinAbilities,
  fetchCourseDigitalTwinAbilityMappings,
  fetchCourseDigitalTwinCourses,
  fetchCourseDigitalTwinPositions,
  fetchCourseDigitalTwinResources,
  fetchCourseDigitalTwinRuntimeEvaluation,
  fetchQuizDefinitions,
  generateCourseInitialGraph,
  generateCourseDigitalTwinAbilityMappingCandidates,
  importCourseDigitalTwinAbilities,
  publishQuizDefinition,
  publishCourseDigitalTwin,
  reviewCourseDigitalTwinAbilityMappings,
  reviewCourseDigitalTwinResource,
  saveQuizDefinition,
  saveCourseDigitalTwinAbilityMappings,
  saveCourseDigitalTwinPosition,
  upsertCourseDigitalTwinStructure,
} from "../../api/teacher";
import type {
  CourseAbilityMapping,
  CourseCareerAbility,
  CourseCareerPosition,
  CourseDigitalTwinResource,
  CourseDigitalTwinSummary,
  CourseGraphNode,
  CourseRuntimeAbilityGap,
  CourseRuntimeChapterRisk,
  CourseRuntimeEvaluation,
  CourseRuntimeNodeIssue,
  QuizDefinition,
} from "../../types/teacher";

type KnowledgePointFormNode = {
  id: string;
  name: string;
};

type SectionFormNode = {
  id: string;
  name: string;
  collapsed: boolean;
  children: KnowledgePointFormNode[];
};

type ChapterFormNode = {
  id: string;
  name: string;
  collapsed: boolean;
  children: SectionFormNode[];
};

type QuizQuestionFormItem = {
  id: string;
  question: string;
  correct: "a" | "b" | "c" | "d";
};

type LeafNodeOption = {
  node_id: string;
  node_name: string;
  pathText: string;
};

type SectionPlacementOption = {
  key: string;
  path: string[];
  pathText: string;
};

type ResourceFilterKey = "all" | "pending" | "enabled" | "disabled";

const courses = ref<CourseDigitalTwinSummary[]>([]);
const selectedSummary = ref<CourseDigitalTwinSummary | null>(null);
const generatedSummary = ref<CourseDigitalTwinSummary | null>(null);
const graphData = ref<CourseGraphNode | null>(null);
const resources = ref<CourseDigitalTwinResource[]>([]);
const positions = ref<CourseCareerPosition[]>([]);
const abilities = ref<CourseCareerAbility[]>([]);
const abilityMappings = ref<CourseAbilityMapping[]>([]);
const runtimeEvaluation = ref<CourseRuntimeEvaluation | null>(null);
const quizDefinitions = ref<QuizDefinition[]>([]);
const abilityMappingFormRef = ref<HTMLElement | null>(null);
const quizDefinitionPanelRef = ref<HTMLElement | null>(null);
const courseBuilderPanelRef = ref<HTMLElement | null>(null);
const resourceReviewPanelRef = ref<HTMLElement | null>(null);
const resourceFilter = ref<ResourceFilterKey>("pending");
const loading = ref(false);
const error = ref("");
const notice = ref("");
const abilityCandidateHint = ref("");
const abilityMappingRuntimeHint = ref("");
const abilityMappingRuntimeContext = ref<{
  ability_id: number;
  gap_type?: string;
  a_sup?: number | null;
  node_id?: string;
  source: "course_runtime_evaluation";
} | null>(null);
const route = useRoute();

const treeForm = ref<ChapterFormNode[]>([
  createChapter("数据采集", [
    createSection("数据采集概述", ["Flume 基础", "Kafka 数据接入"]),
  ]),
]);

const form = reactive({
  course_id: "course_big_data",
  course_name: "大数据分析",
  outline_text: "",
  bind_resource_candidates: true,
  max_resources_per_leaf: 3,
});

const quizForm = reactive<{
  node_id: string;
  title: string;
  definition_id: string;
  questions: QuizQuestionFormItem[];
}>({
  node_id: "",
  title: "",
  definition_id: "",
  questions: [createQuizQuestion()],
});

const positionForm = reactive({
  position_name: "",
  position_type: "primary",
  target_rank: 0,
  source_keyword: "",
});

const abilityImportForm = reactive({
  position_id: 0,
  default_category: "",
  raw_text: "",
});

const abilityMappingForm = reactive({
  ability_id: 0,
  node_id: "",
  support_level: "medium",
  match_reason: "",
  review_status: "draft",
});

const abilityGapDraftForm = reactive({
  visible: false,
  ability_id: 0,
  ability_name: "",
  section_key: "",
  node_name: "",
  description: "",
  resource_keywords: "",
  source_reason: "",
});

const activeCourseId = computed(() => generatedSummary.value?.course_id || selectedSummary.value?.course_id || "");
const activeSummary = computed(() => generatedSummary.value || selectedSummary.value);
const confirmedAbilityMappingCount = computed(() =>
  abilityMappings.value.filter((item) => normalizedReviewStatus(item.review_status) === "confirmed").length,
);
const publishedQuizDefinitionCount = computed(() =>
  quizDefinitions.value.filter((item) => String(item.status || "").toLowerCase() === "published").length,
);
const enabledResourceCount = computed(() =>
  resources.value.filter((item) => item.is_enabled && !item.is_deleted).length,
);
const pendingResourceReviewCount = computed(() =>
  resources.value.filter((item) => !item.is_deleted && normalizedReviewStatus(item.review_status) === "pending").length,
);
const disabledResourceCount = computed(() =>
  resources.value.filter((item) => !item.is_deleted && !item.is_enabled).length,
);
const filteredResources = computed(() => {
  if (resourceFilter.value === "pending") {
    return resources.value.filter((item) => !item.is_deleted && normalizedReviewStatus(item.review_status) === "pending");
  }
  if (resourceFilter.value === "enabled") {
    return resources.value.filter((item) => !item.is_deleted && item.is_enabled);
  }
  if (resourceFilter.value === "disabled") {
    return resources.value.filter((item) => !item.is_deleted && !item.is_enabled);
  }
  return resources.value.filter((item) => !item.is_deleted);
});
const resourceFilterTabs = computed(() => [
  { key: "pending" as const, label: "待审核", count: pendingResourceReviewCount.value },
  { key: "enabled" as const, label: "已启用", count: enabledResourceCount.value },
  { key: "disabled" as const, label: "已禁用", count: disabledResourceCount.value },
  { key: "all" as const, label: "全部", count: resources.value.filter((item) => !item.is_deleted).length },
]);
const pendingAbilityMappingCount = computed(() =>
  abilityMappings.value.filter((item) => !["confirmed", "rejected"].includes(item.review_status)).length,
);
const pendingAbilityMappings = computed(() =>
  abilityMappings.value.filter((item) => !["confirmed", "rejected"].includes(item.review_status)),
);
const outlineText = computed(() => serializeTreeForm());
const canGenerate = computed(() => Boolean(form.course_id.trim() && form.course_name.trim() && outlineText.value.trim()));
const canSavePosition = computed(() => Boolean(activeCourseId.value && positionForm.position_name.trim()));
const canImportAbilities = computed(() =>
  Boolean(activeCourseId.value && abilityImportForm.position_id > 0 && abilityImportForm.raw_text.trim()),
);
const canSaveAbilityMapping = computed(() =>
  Boolean(activeCourseId.value && abilityMappingForm.ability_id > 0 && abilityMappingForm.node_id),
);
const canGenerateAbilityMappingCandidates = computed(() =>
  Boolean(activeCourseId.value && abilities.value.length && leafNodeOptions.value.length),
);
const leafNodeOptions = computed<LeafNodeOption[]>(() => {
  const rows: LeafNodeOption[] = [];

  function walk(node: CourseGraphNode, path: string[]) {
    const name = String(node.name || node.node_id || "未命名节点");
    const nextPath = [...path, name];
    const children = childrenOf(node);
    if (!children.length) {
      rows.push({
        node_id: String(node.node_id || node.id || name),
        node_name: name,
        pathText: nextPath.join(" / "),
      });
      return;
    }
    children.forEach((child) => walk(child, nextPath));
  }

  childrenOf(graphData.value).forEach((node) => walk(node, []));
  return rows;
});
const sectionPlacementOptions = computed<SectionPlacementOption[]>(() => {
  const rows: SectionPlacementOption[] = [];

  function walk(node: CourseGraphNode, path: string[]) {
    const name = String(node.name || node.node_id || "").trim();
    if (!name) return;
    const nextPath = [...path, name];
    const children = childrenOf(node);
    if (nextPath.length >= 2 && children.length && children.some((child) => !childrenOf(child).length)) {
      rows.push({
        key: nextPath.join("///"),
        path: nextPath,
        pathText: nextPath.join(" / "),
      });
    }
    children.forEach((child) => walk(child, nextPath));
  }

  childrenOf(graphData.value).forEach((node) => walk(node, []));
  return rows;
});
const canSaveAbilityGapDraftNode = computed(() =>
  Boolean(
    activeCourseId.value
    && graphData.value
    && abilityGapDraftForm.ability_id > 0
    && abilityGapDraftForm.node_name.trim()
    && abilityGapDraftForm.section_key
  ),
);
const canSaveQuizDefinition = computed(() =>
  Boolean(
    activeCourseId.value
    && quizForm.node_id
    && quizForm.title.trim()
    && quizForm.questions.length
    && quizForm.questions.every((item) => item.question.trim() && item.correct),
  ),
);
const coursePublishState = computed(() => {
  const status = String(activeSummary.value?.lifecycle_status || "draft").toLowerCase();
  if (status === "published") return {code: "published", label: "已发布，学生端可用"};
  if (activeCourseId.value) return {code: "draft", label: "草稿/待确认"};
  return {code: "empty", label: "未建立课程"};
});
const coursePublishSteps = computed(() => [
  {
    key: "structure",
    index: "01",
    title: "课程结构",
    description: activeSummary.value
      ? `${activeSummary.value.node_count} 个节点，${activeSummary.value.leaf_node_count ?? 0} 个叶子知识点`
      : "先录入章节、小节和叶子知识点",
    state: activeSummary.value ? "done" : "todo",
  },
  {
    key: "resources",
    index: "02",
    title: "资源候选",
    description: pendingResourceReviewCount.value
      ? `${pendingResourceReviewCount.value} 个资源仍待教师审核，启用后才进入正式学习中心`
      : enabledResourceCount.value
      ? `${enabledResourceCount.value} 个资源已启用，可支撑学习中心`
      : "资源候选需要教师启用后才进入正式底座",
    state: pendingResourceReviewCount.value ? "pending" : enabledResourceCount.value ? "done" : activeSummary.value ? "pending" : "todo",
  },
  {
    key: "quiz",
    index: "03",
    title: "测验定义",
    description: publishedQuizDefinitionCount.value
      ? `${publishedQuizDefinitionCount.value} 个节点测验已发布`
      : "建议为关键叶子知识点发布正式小测，补齐诊断依据",
    state: publishedQuizDefinitionCount.value ? "done" : activeSummary.value ? "pending" : "todo",
  },
  {
    key: "ability",
    index: "04",
    title: "能力映射",
    description: confirmedAbilityMappingCount.value
      ? `${confirmedAbilityMappingCount.value} 条能力映射已确认`
      : "行业能力映射需教师确认，学生端不展示审核过程",
    state: confirmedAbilityMappingCount.value ? "done" : abilityMappings.value.length ? "pending" : "todo",
  },
  {
    key: "review",
    index: "05",
    title: "教师审核",
    description: pendingAbilityMappingCount.value
      ? `${pendingAbilityMappingCount.value} 条能力映射仍待审核`
      : "关键候选项已处理，可进入发布前确认",
    state: pendingAbilityMappingCount.value ? "pending" : activeSummary.value ? "done" : "todo",
  },
  {
    key: "publish",
    index: "06",
    title: "发布生效",
    description: coursePublishState.value.code === "published"
      ? "已进入学生端、诊断链路和个性化路径"
      : "点击发布课程底座后，学生端才读取正式版本",
    state: coursePublishState.value.code === "published" ? "done" : activeSummary.value ? "pending" : "todo",
  },
]);
const runtimeMetrics = computed(() => runtimeEvaluation.value?.metrics || {});
const runtimeSections = computed<CourseRuntimeEvaluation["sections"]>(() => runtimeEvaluation.value?.sections || {});
const runtimeScoreCards = computed(() => [
  { label: "结构完整", value: runtimeMetrics.value.structure_score, hint: "结构层级与知识点粒度" },
  { label: "资源支撑", value: runtimeMetrics.value.resource_score, hint: "资源覆盖与学习有效性" },
  { label: "测评证据", value: runtimeMetrics.value.assessment_score, hint: "小测、章节作业与代码题证据" },
  { label: "掌握表现", value: runtimeMetrics.value.mastery_score, hint: "学生运行数据中的薄弱点" },
  { label: "能力支撑", value: runtimeMetrics.value.ability_score, hint: "职业能力映射与支撑达成" },
]);
const runtimeResourceGaps = computed(() =>
  runtimeSections.value.resource_coverage_and_effectiveness?.resource_gaps || [],
);
const runtimeAssessmentGaps = computed(() =>
  runtimeSections.value.assessment_evidence_and_learning_effect?.knowledge_point_evidence_gaps || [],
);
const runtimeRiskNodes = computed(() => runtimeSections.value.runtime_weak_points?.risk_nodes || []);
const runtimeChapterRisks = computed(() => runtimeSections.value.runtime_weak_points?.chapter_risks || []);
const runtimeAbilityGaps = computed(() => runtimeSections.value.career_ability_support?.ability_gaps || []);
const runtimeActionItems = computed(() => runtimeEvaluation.value?.action_items || []);
const runtimeUnavailableMetrics = computed(() => runtimeEvaluation.value?.unavailable_metrics || []);
const flatGraphNodes = computed(() => {
  const rows: Array<{ key: string; name: string; depth: number; resourceCount: number }> = [];

  function walk(node: CourseGraphNode, depth: number) {
    const resourcePaths = Array.isArray(node.resource_path)
      ? node.resource_path
      : node.resource_path
        ? [node.resource_path]
        : [];
    rows.push({
      key: `${depth}-${nodeKey(node)}-${rows.length}`,
      name: String(node.name || "未命名节点"),
      depth,
      resourceCount: resourcePaths.length,
    });
    childrenOf(node).forEach((child) => walk(child, depth + 1));
  }

  childrenOf(graphData.value).forEach((node) => walk(node, 0));
  return rows;
});

function childrenOf(node: CourseGraphNode | null | undefined): CourseGraphNode[] {
  if (!node) return [];
  return node.children || node.grandchildren || node["great-grandchildren"] || [];
}

function childKeyOf(node: CourseGraphNode | null | undefined): "children" | "grandchildren" | "great-grandchildren" {
  if (!node) return "children";
  if (Array.isArray(node.children)) return "children";
  if (Array.isArray(node.grandchildren)) return "grandchildren";
  if (Array.isArray(node["great-grandchildren"])) return "great-grandchildren";
  return "children";
}

function ensureChildren(node: CourseGraphNode, key: "children" | "grandchildren" | "great-grandchildren") {
  const existing = node[key];
  if (Array.isArray(existing)) return existing as CourseGraphNode[];
  node[key] = [];
  return node[key] as CourseGraphNode[];
}

function normalizeNodeId(value: string) {
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^\u4e00-\u9fa5a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return (normalized || `node_${Date.now().toString(36)}`).slice(0, 120);
}

function nodeKey(node: CourseGraphNode) {
  return String(node.node_id || node.id || node.name || Math.random());
}

function displayResource(path: string) {
  try {
    const url = new URL(path);
    return `${url.hostname}${url.pathname}`.slice(0, 88);
  } catch {
    return path.slice(0, 88);
  }
}

function supportLevelText(level?: string | null) {
  const mapping: Record<string, string> = {
    high: "强支撑",
    strong: "强支撑",
    medium: "中支撑",
    middle: "中支撑",
    low: "弱支撑",
    weak: "弱支撑",
  };
  return mapping[String(level || "").toLowerCase()] || "支撑待定";
}

function reviewStatusText(status?: string | null) {
  const mapping: Record<string, string> = {
    pending: "待审核",
    confirmed: "已确认",
    rejected: "已驳回",
    draft: "草稿",
    enabled: "已启用",
    disabled: "已禁用",
  };
  return mapping[String(status || "").toLowerCase()] || status || "待审核";
}

function resourceQualityText(status?: string | null) {
  const mapping: Record<string, string> = {
    passed: "质量通过",
    candidate: "候选待查",
    failed: "不可用",
  };
  return mapping[String(status || "").toLowerCase()] || status || "候选待查";
}

function resourceSourceText(source?: string | null) {
  const value = String(source || "").toLowerCase();
  if (value === "external") return "外部资源";
  if (value === "local") return "本地资料";
  return source || "资源";
}

function normalizedReviewStatus(status?: string | null) {
  const normalized = String(status || "pending").toLowerCase();
  if (normalized === "confirmed") return "confirmed";
  if (normalized === "rejected") return "rejected";
  if (normalized === "draft") return "draft";
  return "pending";
}

function mappingEvidenceSummary(mapping: CourseAbilityMapping) {
  const evidence = mapping.evidence && typeof mapping.evidence === "object" ? mapping.evidence : {};
  const values = Object.entries(evidence)
    .filter(([, value]) => value !== undefined && value !== null && String(value).trim())
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${String(value).slice(0, 48)}`);
  if (values.length) {
    return `来源证据：${values.join("；")}`;
  }
  return "暂无详细证据，建议教师结合岗位说明、课程目标和叶子知识点内容人工确认。";
}

function parseAbilityCandidates(rawText: string) {
  const text = rawText.trim();
  if (!text) return [];
  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) {
      return parsed
        .filter((item) => item && typeof item === "object")
        .map((item) => ({
          ability_name: String(item.ability_name || item.name || "").trim(),
          ability_category: String(item.ability_category || item.category || abilityImportForm.default_category || "").trim() || undefined,
          demand_level: String(item.demand_level || item.level || "medium").trim() || "medium",
          source_evidence: item.source_evidence || item.evidence || undefined,
        }))
        .filter((item) => item.ability_name);
    }
  } catch {
    // Fall through to line-based parsing.
  }
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, category, demand] = line.split(/[,\t|，]/).map((item) => item.trim());
      return {
        ability_name: name,
        ability_category: category || abilityImportForm.default_category || undefined,
        demand_level: demand || "medium",
      };
    })
    .filter((item) => item.ability_name);
}

function formatScore(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(1) : "--";
}

function formatPercent(value: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "--";
  return `${(value * 100).toFixed(0)}%`;
}

function healthLevel(score: unknown) {
  if (typeof score !== "number" || !Number.isFinite(score)) return "依据不足";
  if (score >= 80) return "运行较稳";
  if (score >= 60) return "需要关注";
  return "优先维护";
}

function priorityText(priority?: string) {
  const mapping: Record<string, string> = {
    high: "高",
    medium: "中",
    low: "低",
  };
  return mapping[String(priority || "").toLowerCase()] || "待定";
}

function runtimeActionButtonText(type?: string) {
  const mapping: Record<string, string> = {
    structure_issue: "编辑结构",
    resource_gap_or_quality: "处理资源",
    assessment_evidence_gap: "补测评",
    course_runtime_risk: "查看风险点",
    ability_support_gap: "处理能力",
  };
  return mapping[String(type || "")] || "";
}

function handleRuntimeActionItem(type?: string) {
  const normalized = String(type || "");
  if (normalized === "structure_issue") {
    notice.value = "请在课程结构编辑区补充节点说明、拆分过粗知识点或新增草稿节点，保存后再发布新版课程底座。";
    courseBuilderPanelRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }
  if (normalized === "resource_gap_or_quality") {
    const firstGap = runtimeResourceGaps.value[0];
    resourceFilter.value = pendingResourceReviewCount.value ? "pending" : "all";
    if (firstGap) {
      prepareResourceGapBinding(firstGap);
    } else {
      notice.value = "请在资源审核区启用、禁用或替换候选资源。";
      resourceReviewPanelRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    return;
  }
  if (normalized === "assessment_evidence_gap") {
    const firstGap = runtimeAssessmentGaps.value[0];
    if (firstGap) {
      prepareAssessmentGapQuiz(firstGap);
    } else {
      notice.value = "请为关键叶子知识点补充正式小测，章节实践题请到作业模块确认覆盖知识点。";
      quizDefinitionPanelRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    return;
  }
  if (normalized === "course_runtime_risk") {
    const firstRisk = runtimeRiskNodes.value[0];
    if (firstRisk?.node_id) {
      prepareAssessmentGapQuiz(firstRisk);
      notice.value = "已把高风险知识点带入小测编辑区；也可同步检查资源与作业覆盖。";
    } else {
      notice.value = "请优先查看运行风险列表中的高风险知识点，并补资源、补测评或调整教学重点。";
    }
    return;
  }
  if (normalized === "ability_support_gap") {
    const firstGap = runtimeAbilityGaps.value[0];
    if (firstGap?.ability_id) {
      prepareAbilityGapMapping(firstGap);
    } else {
      notice.value = "请导入岗位能力候选并生成能力-知识点映射，无法匹配时补充草稿知识点。";
      abilityMappingFormRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }
}

function runtimeNodeTitle(item: CourseRuntimeNodeIssue) {
  return item.node_path?.length
    ? item.node_path.join(" / ")
    : item.node_name || item.node_id || "课程结构";
}

function runtimeAbilityTitle(item: CourseRuntimeAbilityGap) {
  return [item.position_name, item.ability_name].filter(Boolean).join(" / ") || "职业能力";
}

function runtimeAbilityGapTypeText(gapType?: string) {
  const mapping: Record<string, string> = {
    missing_mapping: "缺少能力映射",
    primary_high_demand_low_support: "高需求能力支撑不足",
  };
  return mapping[String(gapType || "")] || "能力支撑缺口";
}

async function prepareResourceGapBinding(item: CourseRuntimeNodeIssue) {
  if (!activeCourseId.value) return;
  notice.value = `正在为 ${runtimeNodeTitle(item)} 补充资源候选...`;
  await bindResources();
}

async function prepareAssessmentGapQuiz(item: CourseRuntimeNodeIssue) {
  if (!item.node_id) return;
  const targetNode = leafNodeOptions.value.find((node) => node.node_id === item.node_id);
  resetQuizFormForNode(targetNode?.node_id || String(item.node_id));
  notice.value = `已将测评缺口带入节点测验表单：${targetNode?.pathText || runtimeNodeTitle(item)}`;
  requestAnimationFrame(() => {
    quizDefinitionPanelRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  loading.value = true;
  setBusyMessage();
  try {
    await loadQuizDefinitions();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "测验定义加载失败";
  } finally {
    loading.value = false;
  }
}

function prepareAbilityGapMapping(item: CourseRuntimeAbilityGap) {
  if (!item.ability_id) return;
  abilityMappingForm.ability_id = Number(item.ability_id);
  const missingNodes = Array.isArray(item.missing_mastery_nodes)
    ? item.missing_mastery_nodes.map((nodeId) => String(nodeId || "")).filter(Boolean)
    : [];
  const targetNode = leafNodeOptions.value.find((node) => missingNodes.includes(node.node_id));
  abilityMappingForm.node_id = targetNode?.node_id || "";
  abilityMappingForm.support_level = "high";
  abilityMappingForm.review_status = "draft";
  const gapTypeText = runtimeAbilityGapTypeText(item.gap_type);
  const nodeMatchText = targetNode
    ? `已匹配缺口知识点：${targetNode.pathText}`
    : missingNodes.length
      ? "评估返回的缺口节点未匹配到当前课程叶子知识点，请教师重新选择。"
      : "评估未给出可直接映射的叶子知识点，请教师根据能力要求选择。";
  abilityMappingForm.match_reason = [
    "来源：课程运行评估",
    `缺口类型：${gapTypeText}`,
    typeof item.a_sup === "number" ? `能力支撑分：${formatScore(item.a_sup)}` : "",
    item.reason || "课程运行评估提示该能力存在支撑缺口",
    item.suggested_action || "请教师补充或复核能力与叶子知识点支撑关系",
    nodeMatchText,
    "保存为草稿；教师确认并发布后才影响正式能力映射。",
  ].filter(Boolean).join("；");
  abilityMappingRuntimeContext.value = {
    ability_id: Number(item.ability_id),
    gap_type: item.gap_type,
    a_sup: item.a_sup,
    node_id: targetNode?.node_id,
    source: "course_runtime_evaluation",
  };
  abilityMappingRuntimeHint.value = targetNode
    ? `已从课程运行评估带入「${runtimeAbilityTitle(item)}」的${gapTypeText}，当前仅保存为草稿，确认发布后才进入正式能力映射。`
    : `已从课程运行评估带入「${runtimeAbilityTitle(item)}」的${gapTypeText}，但没有可直接预填的叶子知识点，请教师手动选择后再保存。`;
  notice.value = targetNode
    ? "已将能力缺口带入映射表单，默认保存为草稿。"
    : "已将能力缺口带入映射表单，请先选择叶子知识点。";
  requestAnimationFrame(() => {
    abilityMappingFormRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}

function prepareAbilityGapDraftNode(item: CourseRuntimeAbilityGap) {
  if (!item.ability_id) return;
  const title = runtimeAbilityTitle(item);
  const abilityName = String(item.ability_name || title.split(" / ").pop() || "职业能力").trim();
  abilityGapDraftForm.visible = true;
  abilityGapDraftForm.ability_id = Number(item.ability_id);
  abilityGapDraftForm.ability_name = abilityName;
  abilityGapDraftForm.section_key = sectionPlacementOptions.value[0]?.key || "";
  abilityGapDraftForm.node_name = abilityName.endsWith("实践") ? abilityName : `${abilityName}实践`;
  abilityGapDraftForm.description = [
    "来源：课程运行评估",
    `缺口类型：${runtimeAbilityGapTypeText(item.gap_type)}`,
    typeof item.a_sup === "number" ? `能力支撑分：${formatScore(item.a_sup)}` : "",
    item.reason || "该职业能力缺少足够课程叶子知识点支撑",
    "教师确认后先进入草稿图谱，不直接发布。",
  ].filter(Boolean).join("；");
  abilityGapDraftForm.resource_keywords = `${abilityName} 教程 B站 YouTube CSDN`;
  abilityGapDraftForm.source_reason = item.suggested_action || item.reason || "";
  notice.value = "已生成补知识点草稿建议，请确认名称和放置位置后保存。";
  requestAnimationFrame(() => {
    abilityMappingFormRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}

function closeAbilityGapDraftForm() {
  abilityGapDraftForm.visible = false;
  abilityGapDraftForm.node_name = "";
  abilityGapDraftForm.description = "";
  abilityGapDraftForm.resource_keywords = "";
  abilityGapDraftForm.source_reason = "";
}

function findGraphNodeByPath(path: string[]) {
  let currentChildren = childrenOf(graphData.value);
  let current: CourseGraphNode | null = null;
  for (const segment of path) {
    current = currentChildren.find((node) => String(node.name || node.node_id || "").trim() === segment) || null;
    if (!current) return null;
    currentChildren = childrenOf(current);
  }
  return current;
}

async function saveAbilityGapDraftNode() {
  const courseId = activeCourseId.value;
  if (!courseId || !graphData.value || !canSaveAbilityGapDraftNode.value) return;
  const placement = sectionPlacementOptions.value.find((item) => item.key === abilityGapDraftForm.section_key);
  if (!placement) {
    error.value = "请选择知识点放置位置";
    return;
  }
  const targetSection = findGraphNodeByPath(placement.path);
  if (!targetSection) {
    error.value = "未找到图谱中的目标小节，请刷新课程后重试";
    return;
  }

  const graphCopy = JSON.parse(JSON.stringify(graphData.value)) as CourseGraphNode;
  graphData.value = graphCopy;
  const copiedSection = findGraphNodeByPath(placement.path);
  if (!copiedSection) {
    error.value = "图谱草稿同步失败，请刷新课程后重试";
    return;
  }
  const leafChildrenKey = childKeyOf(copiedSection) === "children" ? "children" : "great-grandchildren";
  const leaves = ensureChildren(copiedSection, leafChildrenKey);
  const nodeName = abilityGapDraftForm.node_name.trim();
  const baseNodeId = normalizeNodeId(nodeName);
  const existingIds = new Set(leafNodeOptions.value.map((item) => item.node_id));
  let nodeId = baseNodeId;
  let index = 2;
  while (existingIds.has(nodeId)) {
    nodeId = `${baseNodeId}_${index}`;
    index += 1;
  }
  leaves.push({
    name: nodeName,
    node_id: nodeId,
    draft_source: "career_ability_gap",
    lifecycle_status: "draft",
    description: abilityGapDraftForm.description,
    resource_keywords: abilityGapDraftForm.resource_keywords,
    ability_id: abilityGapDraftForm.ability_id,
  });

  loading.value = true;
  setBusyMessage("正在保存草稿知识点并绑定资源候选...");
  try {
    const structureData = await upsertCourseDigitalTwinStructure({
      course_id: courseId,
      course_name: form.course_name,
      graph_data: graphCopy as unknown as Record<string, unknown>,
      lifecycle_status: "draft",
    });
    selectedSummary.value = structureData.summary;
    generatedSummary.value = structureData.summary;
    treeForm.value = graphToTree(graphCopy);
    await bindCourseResourceCandidates({
      course_id: courseId,
      max_resources_per_leaf: form.max_resources_per_leaf,
      overwrite: false,
      review_status: "pending",
    });
    await selectCourse(courseId);
    abilityMappingForm.ability_id = abilityGapDraftForm.ability_id;
    abilityMappingForm.node_id = nodeId;
    abilityMappingForm.support_level = "high";
    abilityMappingForm.review_status = "draft";
    abilityMappingForm.match_reason = [
      "来源：职业能力缺口补知识点流程",
      abilityGapDraftForm.description,
      "新增知识点和资源候选仍为草稿/待审核，教师确认并发布新版课程底座后才进入学生端。",
    ].filter(Boolean).join("；");
    abilityMappingRuntimeContext.value = {
      ability_id: abilityGapDraftForm.ability_id,
      gap_type: "draft_node_added",
      node_id: nodeId,
      source: "course_runtime_evaluation",
    };
    abilityMappingRuntimeHint.value = `已新增草稿知识点「${nodeName}」并绑定资源候选，请继续保存/确认能力映射后发布新版课程底座。`;
    abilityGapDraftForm.visible = false;
    notice.value = `已新增草稿知识点「${nodeName}」，资源候选已进入教师审核。`;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "能力缺口草稿知识点保存失败";
    notice.value = "";
  } finally {
    loading.value = false;
  }
}

function runtimeChapterTitle(item: CourseRuntimeChapterRisk) {
  return item.chapter || "章节";
}

function createId(prefix: string) {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function createPoint(name = ""): KnowledgePointFormNode {
  return { id: createId("point"), name };
}

function createSection(name = "", points: string[] = [""]): SectionFormNode {
  return {
    id: createId("section"),
    name,
    collapsed: false,
    children: points.length ? points.map((item) => createPoint(item)) : [createPoint()],
  };
}

function createChapter(name = "", sections: SectionFormNode[] = [createSection()]): ChapterFormNode {
  return {
    id: createId("chapter"),
    name,
    collapsed: false,
    children: sections.length ? sections : [createSection()],
  };
}

function createQuizQuestion(question = "", correct: "a" | "b" | "c" | "d" = "a"): QuizQuestionFormItem {
  return {
    id: createId("quiz_question"),
    question,
    correct,
  };
}

function resetQuizFormForNode(nodeId = quizForm.node_id) {
  const node = leafNodeOptions.value.find((item) => item.node_id === nodeId);
  quizForm.node_id = nodeId;
  quizForm.definition_id = "";
  quizForm.title = node ? `${node.node_name} 小测` : "";
  quizForm.questions = [createQuizQuestion()];
}

function resetAbilityMappingNode(nodeId = abilityMappingForm.node_id) {
  abilityMappingForm.node_id = nodeId || leafNodeOptions.value[0]?.node_id || "";
}

function addQuizQuestion() {
  quizForm.questions.push(createQuizQuestion());
}

function removeQuizQuestion(index: number) {
  if (quizForm.questions.length <= 1) return;
  quizForm.questions.splice(index, 1);
}

function loadQuizDefinitionIntoForm(definition: QuizDefinition) {
  quizForm.node_id = definition.node_id || quizForm.node_id;
  quizForm.definition_id = definition.definition_id || "";
  quizForm.title = definition.title || "";
  quizForm.questions = (definition.questions || []).map((item) =>
    createQuizQuestion(
      String(item.question || ""),
      ["a", "b", "c", "d"].includes(String(item.correct || "").toLowerCase())
        ? (String(item.correct).toLowerCase() as "a" | "b" | "c" | "d")
        : "a",
    ),
  );
  if (!quizForm.questions.length) {
    quizForm.questions = [createQuizQuestion()];
  }
  notice.value = "已载入测验定义，可继续编辑后保存草稿或发布。";
}

function quizDefinitionStatusText(status: string) {
  const mapping: Record<string, string> = {
    draft: "草稿",
    published: "已发布",
  };
  return mapping[String(status || "").toLowerCase()] || status || "未知";
}

function addChapter() {
  treeForm.value.push(createChapter());
}

function removeChapter(index: number) {
  if (treeForm.value.length <= 1) return;
  treeForm.value.splice(index, 1);
}

function addSection(chapter: ChapterFormNode) {
  chapter.children.push(createSection());
  chapter.collapsed = false;
}

function removeSection(chapter: ChapterFormNode, index: number) {
  if (chapter.children.length <= 1) return;
  chapter.children.splice(index, 1);
}

function addKnowledgePoint(section: SectionFormNode) {
  section.children.push(createPoint());
  section.collapsed = false;
}

function removeKnowledgePoint(section: SectionFormNode, index: number) {
  if (section.children.length <= 1) return;
  section.children.splice(index, 1);
}

function serializeTreeForm() {
  const lines: string[] = [];
  treeForm.value.forEach((chapter, chapterIndex) => {
    const chapterName = chapter.name.trim();
    if (!chapterName) return;
    lines.push(`第${chapterIndex + 1}章 ${chapterName}`);
    chapter.children.forEach((section, sectionIndex) => {
      const sectionName = section.name.trim();
      if (!sectionName) return;
      lines.push(`  ${chapterIndex + 1}.${sectionIndex + 1} ${sectionName}`);
      section.children.forEach((point) => {
        const pointName = point.name.trim();
        if (pointName) lines.push(`    ${pointName}`);
      });
    });
  });
  return lines.join("\n");
}

function buildOutlineText() {
  form.outline_text = serializeTreeForm();
  return form.outline_text;
}

function graphToTree(node: CourseGraphNode | null): ChapterFormNode[] {
  const chapters = childrenOf(node).map((chapter) => {
    const chapterChildren = childrenOf(chapter);
    const isLeaves = chapterChildren.length > 0 && chapterChildren.every((child) => childrenOf(child).length === 0);
    const sections = isLeaves
      ? [createSection("默认小节", chapterChildren.map((point) => String(point.name || "")))]
      : chapterChildren.map((section) => {
          const sectionChildren = childrenOf(section);
          if (sectionChildren.length === 0) {
            return createSection(String(section.name || ""), [String(section.name || "")]);
          }
          return createSection(
            String(section.name || ""),
            sectionChildren.map((point) => String(point.name || "")),
          );
        });
    return createChapter(String(chapter.name || ""), sections);
  });
  return normalizeTree(chapters);
}

function normalizeTree(chapters: ChapterFormNode[]) {
  const normalized = chapters.length ? chapters : [createChapter("数据采集")];
  normalized.forEach((chapter) => {
    if (!chapter.children.length) chapter.children.push(createSection("知识点小节", ["核心知识点"]));
    chapter.children.forEach((section) => {
      if (!section.children.length) section.children.push(createPoint("核心知识点"));
    });
  });
  return normalized;
}

function setBusyMessage(message = "") {
  error.value = "";
  notice.value = message;
}

async function loadCourses() {
  loading.value = true;
  setBusyMessage();
  try {
    const data = await fetchCourseDigitalTwinCourses();
    courses.value = data.courses || [];
    if (!selectedSummary.value && courses.value.length) {
      const requestedCourseId = typeof route.query.course_id === "string" ? route.query.course_id : "";
      const targetCourse = courses.value.find((course) => course.course_id === requestedCourseId) || courses.value[0];
      await selectCourse(targetCourse.course_id);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "课程列表加载失败";
  } finally {
    loading.value = false;
  }
}

async function selectCourse(courseId: string) {
  if (!courseId) return;
  loading.value = true;
  setBusyMessage();
  try {
    const data = await fetchCourseDigitalTwin(courseId);
    selectedSummary.value = data.summary;
    generatedSummary.value = null;
    graphData.value = data.graph_data as CourseGraphNode;
    treeForm.value = graphToTree(graphData.value);
    buildOutlineText();
    form.course_id = data.summary.course_id;
    form.course_name = data.summary.course_name;
    resetQuizFormForNode(leafNodeOptions.value[0]?.node_id || "");
    resetAbilityMappingNode(leafNodeOptions.value[0]?.node_id || "");
    await loadResources(courseId);
    await loadAbilityRelations(courseId);
    await loadQuizDefinitions();
    await loadRuntimeEvaluation(courseId);
    await focusRequestedPanel();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "课程详情加载失败";
  } finally {
    loading.value = false;
  }
}

async function generateInitialGraph() {
  loading.value = true;
  setBusyMessage("正在生成课程图谱...");
  try {
    const data = await generateCourseInitialGraph({
      course_id: form.course_id,
      course_name: form.course_name,
      outline_text: buildOutlineText(),
      lifecycle_status: "draft",
      bind_resource_candidates: form.bind_resource_candidates,
      max_resources_per_leaf: form.max_resources_per_leaf,
    });
    generatedSummary.value = data.summary;
    selectedSummary.value = data.summary;
    graphData.value = data.graph_data;
    resetQuizFormForNode(leafNodeOptions.value[0]?.node_id || "");
    resetAbilityMappingNode(leafNodeOptions.value[0]?.node_id || "");
    notice.value = `已生成 ${data.validation.node_count} 个节点、${data.validation.leaf_node_count} 个叶子知识点`;
    await loadResources(data.course_id);
    await loadAbilityRelations(data.course_id);
    await loadQuizDefinitions();
    await loadRuntimeEvaluation(data.course_id);
    await refreshCourseListOnly();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "初始图谱生成失败";
    notice.value = "";
  } finally {
    loading.value = false;
  }
}

async function bindResources() {
  const courseId = activeCourseId.value;
  if (!courseId) return;
  loading.value = true;
  setBusyMessage("正在绑定资源候选...");
  try {
    const data = await bindCourseResourceCandidates({
      course_id: courseId,
      max_resources_per_leaf: form.max_resources_per_leaf,
      overwrite: false,
      review_status: "pending",
    });
    generatedSummary.value = data.summary;
    selectedSummary.value = data.summary;
    graphData.value = data.graph_data;
    resources.value = data.resources;
    await loadAbilityRelations(courseId);
    await loadRuntimeEvaluation(courseId);
    notice.value = `已新增 ${data.bind_result.attached_resources} 条资源候选，${data.review_marked_count} 条进入审核`;
    await refreshCourseListOnly();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "资源候选绑定失败";
    notice.value = "";
  } finally {
    loading.value = false;
  }
}

async function loadResources(courseId: string) {
  if (!courseId) return;
  const data = await fetchCourseDigitalTwinResources(courseId);
  resources.value = data.resources || [];
}

async function loadAbilityRelations(courseId: string) {
  if (!courseId) return;
  const [positionData, abilityData, mappingData] = await Promise.all([
    fetchCourseDigitalTwinPositions(courseId),
    fetchCourseDigitalTwinAbilities(courseId),
    fetchCourseDigitalTwinAbilityMappings(courseId),
  ]);
  positions.value = positionData.positions || [];
  abilities.value = abilityData.abilities || [];
  abilityMappings.value = mappingData.mappings || [];
}

async function focusRequestedPanel() {
  if (route.query.focus !== "ability-mapping") return;
  await nextTick();
  abilityMappingFormRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function loadQuizDefinitions() {
  const courseId = activeCourseId.value;
  if (!courseId || !quizForm.node_id) {
    quizDefinitions.value = [];
    return;
  }
  const data = await fetchQuizDefinitions({
    course_id: courseId,
    node_id: quizForm.node_id,
  });
  quizDefinitions.value = data.definitions || [];
}

async function handleQuizNodeChange() {
  resetQuizFormForNode(quizForm.node_id);
  loading.value = true;
  setBusyMessage();
  try {
    await loadQuizDefinitions();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "测验定义加载失败";
  } finally {
    loading.value = false;
  }
}

async function saveCurrentQuizDefinition(status: "draft" | "published") {
  const courseId = activeCourseId.value;
  if (!courseId || !canSaveQuizDefinition.value) return;
  loading.value = true;
  setBusyMessage();
  try {
    const data = await saveQuizDefinition({
      course_id: courseId,
      node_id: quizForm.node_id,
      title: quizForm.title,
      status,
      definition_id: quizForm.definition_id || undefined,
      questions: quizForm.questions.map((item) => ({
        topic: quizForm.node_id,
        question: item.question,
        correct: item.correct,
      })),
    });
    quizForm.definition_id = data.definition.definition_id;
    await loadQuizDefinitions();
    await loadRuntimeEvaluation(courseId);
    notice.value = status === "published" ? "测验定义已发布" : "测验草稿已保存";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "测验定义保存失败";
  } finally {
    loading.value = false;
  }
}

async function publishExistingQuizDefinition(definitionId: string) {
  const courseId = activeCourseId.value;
  if (!courseId || !quizForm.node_id || !definitionId) return;
  loading.value = true;
  setBusyMessage();
  try {
    const data = await publishQuizDefinition({
      definition_id: definitionId,
      course_id: courseId,
      node_id: quizForm.node_id,
    });
    loadQuizDefinitionIntoForm(data.definition);
    await loadQuizDefinitions();
    await loadRuntimeEvaluation(courseId);
    notice.value = "测验定义已发布";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "测验定义发布失败";
  } finally {
    loading.value = false;
  }
}

async function loadRuntimeEvaluation(courseId: string) {
  if (!courseId) {
    runtimeEvaluation.value = null;
    return;
  }
  const data = await fetchCourseDigitalTwinRuntimeEvaluation(courseId);
  runtimeEvaluation.value = data.evaluation || null;
}

async function refreshRuntimeEvaluation() {
  const courseId = activeCourseId.value;
  if (!courseId) return;
  loading.value = true;
  setBusyMessage();
  try {
    await loadRuntimeEvaluation(courseId);
    notice.value = "课程运行评估已刷新";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "课程运行评估刷新失败";
  } finally {
    loading.value = false;
  }
}

async function refreshAbilityMappings() {
  const courseId = activeCourseId.value;
  if (!courseId) return;
  loading.value = true;
  setBusyMessage();
  try {
    await loadAbilityRelations(courseId);
    await loadRuntimeEvaluation(courseId);
    notice.value = "能力映射已刷新";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "能力映射刷新失败";
  } finally {
    loading.value = false;
  }
}

async function savePosition() {
  const courseId = activeCourseId.value;
  if (!courseId || !canSavePosition.value) return;
  loading.value = true;
  setBusyMessage();
  try {
    const data = await saveCourseDigitalTwinPosition({
      course_id: courseId,
      position_name: positionForm.position_name,
      position_type: positionForm.position_type,
      target_rank: Number(positionForm.target_rank || 0),
      source_keyword: positionForm.source_keyword || null,
    });
    positions.value = data.positions || [];
    const savedPositionId = data.position?.position_id || 0;
    if (savedPositionId) {
      abilityImportForm.position_id = savedPositionId;
    }
    positionForm.position_name = "";
    positionForm.source_keyword = "";
    await loadAbilityRelations(courseId);
    await loadRuntimeEvaluation(courseId);
    notice.value = "岗位方向已保存，可继续导入能力候选";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "岗位方向保存失败";
  } finally {
    loading.value = false;
  }
}

async function importAbilities() {
  const courseId = activeCourseId.value;
  if (!courseId || !canImportAbilities.value) return;
  const candidates = parseAbilityCandidates(abilityImportForm.raw_text);
  if (!candidates.length) {
    error.value = "未识别到有效能力候选";
    return;
  }
  loading.value = true;
  setBusyMessage();
  try {
    const data = await importCourseDigitalTwinAbilities({
      course_id: courseId,
      position_id: abilityImportForm.position_id,
      abilities: candidates,
    });
    abilities.value = data.abilities || [];
    abilityImportForm.raw_text = "";
    await loadAbilityRelations(courseId);
    await loadRuntimeEvaluation(courseId);
    abilityCandidateHint.value = "能力候选已导入，可继续生成待审核的能力-知识点映射候选。";
    notice.value = `已导入 ${data.import_result?.saved ?? candidates.length} 个能力候选`;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "能力候选导入失败";
  } finally {
    loading.value = false;
  }
}

async function generateAbilityMappingCandidates() {
  const courseId = activeCourseId.value;
  if (!courseId || !canGenerateAbilityMappingCandidates.value) return;
  loading.value = true;
  setBusyMessage("正在生成能力映射候选...");
  try {
    const data = await generateCourseDigitalTwinAbilityMappingCandidates({
      course_id: courseId,
      max_candidates_per_ability: 3,
      min_score: 0.24,
    });
    abilityMappings.value = data.mappings || [];
    await loadRuntimeEvaluation(courseId);
    const result = data.candidate_result;
    const generated = result?.generated ?? 0;
    const skipped = result?.skipped?.length ?? 0;
    const rejected = result?.rejected?.length ?? 0;
    abilityCandidateHint.value = skipped
      ? `已生成 ${generated} 条待审核候选，${skipped} 个能力未达到匹配阈值，需要教师手动补映射或补知识点。`
      : `已生成 ${generated} 条待审核候选，请教师逐条确认后再发布。`;
    notice.value = rejected
      ? `映射候选已生成，${rejected} 条未通过叶子知识点校验`
      : abilityCandidateHint.value;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "能力映射候选生成失败";
    abilityCandidateHint.value = "";
  } finally {
    loading.value = false;
  }
}

async function saveAbilityMapping() {
  const courseId = activeCourseId.value;
  if (!courseId || !canSaveAbilityMapping.value) return;
  const runtimeContext =
    abilityMappingRuntimeContext.value?.ability_id === abilityMappingForm.ability_id
      ? abilityMappingRuntimeContext.value
      : null;
  loading.value = true;
  setBusyMessage();
  try {
    const data = await saveCourseDigitalTwinAbilityMappings({
      course_id: courseId,
      mappings: [
        {
          ability_id: abilityMappingForm.ability_id,
          node_id: abilityMappingForm.node_id,
          support_level: abilityMappingForm.support_level,
          match_reason: abilityMappingForm.match_reason || "教师手动确认能力与知识点支撑关系",
          review_status: abilityMappingForm.review_status,
          evidence: runtimeContext
            ? {
                source: runtimeContext.source,
                gap_type: runtimeContext.gap_type,
                a_sup: runtimeContext.a_sup,
                suggested_node_id: runtimeContext.node_id || null,
              }
            : {
                source: "teacher_manual_mapping",
              },
        },
      ],
    });
    abilityMappings.value = data.mappings || [];
    abilityMappingForm.match_reason = "";
    abilityMappingForm.review_status = "draft";
    abilityMappingRuntimeHint.value = "";
    abilityMappingRuntimeContext.value = null;
    await loadRuntimeEvaluation(courseId);
    const rejected = data.mapping_result?.rejected || [];
    notice.value = rejected.length
      ? `能力映射已提交，${rejected.length} 条未通过校验`
      : "能力映射已保存";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "能力映射保存失败";
  } finally {
    loading.value = false;
  }
}

async function reviewAbilityMapping(mapping: CourseAbilityMapping, reviewStatus: "confirmed" | "rejected") {
  const courseId = activeCourseId.value;
  if (!courseId) return;
  loading.value = true;
  setBusyMessage();
  try {
    const data = await reviewCourseDigitalTwinAbilityMappings({
      course_id: courseId,
      mappings: [
        {
          mapping_id: mapping.mapping_id,
          review_status: reviewStatus,
          support_level: mapping.support_level,
        },
      ],
    });
    abilityMappings.value = data.mappings || [];
    await loadRuntimeEvaluation(courseId);
    notice.value = reviewStatus === "confirmed" ? "能力映射已确认" : "能力映射已驳回";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "能力映射审核失败";
  } finally {
    loading.value = false;
  }
}

async function reviewPendingAbilityMappings(reviewStatus: "confirmed" | "rejected") {
  const courseId = activeCourseId.value;
  const targets = pendingAbilityMappings.value;
  if (!courseId || !targets.length) return;
  loading.value = true;
  setBusyMessage();
  try {
    const data = await reviewCourseDigitalTwinAbilityMappings({
      course_id: courseId,
      mappings: targets.map((mapping) => ({
        mapping_id: mapping.mapping_id,
        review_status: reviewStatus,
        support_level: mapping.support_level,
      })),
    });
    abilityMappings.value = data.mappings || [];
    await loadRuntimeEvaluation(courseId);
    notice.value = reviewStatus === "confirmed"
      ? `已批量确认 ${data.updated ?? targets.length} 条能力映射`
      : `已批量驳回 ${data.updated ?? targets.length} 条能力映射`;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "能力映射批量审核失败";
  } finally {
    loading.value = false;
  }
}

async function refreshResources() {
  const courseId = activeCourseId.value;
  if (!courseId) return;
  loading.value = true;
  setBusyMessage();
  try {
    await loadResources(courseId);
    await loadRuntimeEvaluation(courseId);
    notice.value = "资源清单已刷新";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "资源清单刷新失败";
  } finally {
    loading.value = false;
  }
}

async function refreshCourseListOnly() {
  const data = await fetchCourseDigitalTwinCourses();
  courses.value = data.courses || [];
}

async function updateCourseResourceReview(resource: CourseDigitalTwinResource, enabled: boolean) {
  const data = await reviewCourseDigitalTwinResource({
    course_id: resource.course_id,
    node_id: resource.node_id,
    resource_path: resource.resource_path,
    is_enabled: enabled,
    review_status: enabled ? "enabled" : "disabled",
    quality_status: enabled ? "passed" : "candidate",
  });
  selectedSummary.value = data.summary;
  generatedSummary.value = data.summary;
}

async function setResourceEnabled(resource: CourseDigitalTwinResource, enabled: boolean) {
  loading.value = true;
  setBusyMessage();
  try {
    await updateCourseResourceReview(resource, enabled);
    await loadResources(resource.course_id);
    await loadRuntimeEvaluation(resource.course_id);
    notice.value = enabled ? "资源已启用" : "资源已禁用";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "资源审核失败";
  } finally {
    loading.value = false;
  }
}

async function batchEnablePendingResources() {
  const courseId = activeCourseId.value;
  const targets = resources.value.filter(
    (item) => !item.is_deleted && normalizedReviewStatus(item.review_status) === "pending",
  );
  if (!courseId || !targets.length) return;
  loading.value = true;
  setBusyMessage(`正在批量启用 ${targets.length} 条待审核资源...`);
  try {
    await Promise.all(targets.map((resource) => updateCourseResourceReview(resource, true)));
    await loadResources(courseId);
    await loadRuntimeEvaluation(courseId);
    await refreshCourseListOnly();
    resourceFilter.value = "enabled";
    notice.value = `已启用 ${targets.length} 条资源，资源审核队列已更新`;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "资源批量审核失败";
    notice.value = "";
  } finally {
    loading.value = false;
  }
}

async function publishCurrentCourse() {
  const courseId = activeCourseId.value;
  if (!courseId) return;
  loading.value = true;
  setBusyMessage("正在发布课程底座...");
  try {
    const data = await publishCourseDigitalTwin(courseId);
    selectedSummary.value = data.summary;
    generatedSummary.value = data.summary;
    await loadRuntimeEvaluation(courseId);
    notice.value = "课程底座已发布";
    await refreshCourseListOnly();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "课程发布失败";
    notice.value = "";
  } finally {
    loading.value = false;
  }
}

watch(
  () => abilityMappingForm.ability_id,
  (abilityId) => {
    if (abilityMappingRuntimeContext.value && abilityMappingRuntimeContext.value.ability_id !== abilityId) {
      abilityMappingRuntimeContext.value = null;
      abilityMappingRuntimeHint.value = "";
    }
  },
);

onMounted(loadCourses);
</script>

<style scoped>
.teacher-course-twin-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.course-twin-hero-actions,
.action-row,
.builder-options,
.resource-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.course-twin-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 24px;
  align-items: start;
}

.course-twin-grid.lower {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 24px;
  align-items: start;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.section-heading h3 {
  margin: 2px 0 0;
}

.course-publish-flow {
  display: grid;
  gap: 14px;
  border-left: 5px solid #0f766e;
  background: #ffffff;
}

.course-publish-steps {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.course-publish-step {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 10px;
  min-height: 118px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.course-publish-step > span {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 900;
}

.course-publish-step strong {
  display: block;
  margin-bottom: 6px;
  color: #0f172a;
  font-size: 14px;
}

.course-publish-step p {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

.course-publish-step.is-done {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.course-publish-step.is-done > span {
  color: #ffffff;
  background: #16a34a;
}

.course-publish-step.is-pending {
  border-color: #fde68a;
  background: #fffbeb;
}

.course-publish-step.is-pending > span {
  color: #92400e;
  background: #fef3c7;
}

.course-publish-boundary {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 14px;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  background: #eff6ff;
  color: #1e3a8a;
  line-height: 1.6;
}

.course-publish-boundary strong {
  flex: 0 0 auto;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-grid label,
.compact-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  color: #4b5563;
  font-size: 13px;
}

.teacher-course-twin-shell select.input {
  min-width: 112px;
  padding-right: 42px;
  text-overflow: ellipsis;
}

.builder-options {
  justify-content: space-between;
  margin: 12px 0;
}

.tree-editor {
  margin-top: 14px;
  border: none;
  border-radius: 12px;
  background:
    linear-gradient(90deg, rgba(37, 99, 235, 0.04) 0 1px, transparent 1px 100%) 34px 0 / 28px 100%,
    #f8fbff;
  box-shadow: inset 0 2px 10px rgba(15, 23, 42, 0.02), 0 0 0 1px rgba(219, 228, 240, 0.6);
  overflow: hidden;
}

.tree-editor-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 13px 14px;
  border-bottom: 1px solid rgba(219, 228, 240, 0.6);
  background: #ffffff;
}

.tree-editor-head p {
  margin: 3px 0 0;
  color: #64748b;
  font-size: 12px;
}

.field-label {
  display: block;
  color: #1f2937;
  font-size: 13px;
  font-weight: 800;
}

.tree-add-root {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  border: 1px solid #bfdbfe;
  border-radius: 7px;
  padding: 0 10px;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.2s;
}

.tree-add-root:hover {
  background: #dbeafe;
}

.tree-add-root svg,
.tree-toggle svg,
.tree-icon-btn svg {
  width: 14px;
  height: 14px;
}

.course-tree-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 430px;
  overflow: auto;
  padding: 16px;
}

.tree-node {
  position: relative;
  min-width: 500px;
}

.tree-row {
  display: grid;
  grid-template-columns: 28px 34px 76px minmax(100px, 1fr) auto;
  gap: 8px;
  align-items: center;
  min-height: 46px;
  border: 1px solid rgba(220, 230, 242, 0.6);
  border-radius: 10px;
  padding: 7px 10px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.02);
  transition: all 0.2s ease;
}

.tree-row:hover {
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
  border-color: rgba(191, 219, 254, 0.8);
}

.tree-row--chapter {
  border-color: #bfdbfe;
  background: #ffffff;
}

.tree-row--section {
  grid-template-columns: 28px 34px 58px minmax(100px, 1fr) auto;
  background: #fbfdff;
}

.tree-node--leaf {
  display: grid;
  grid-template-columns: 28px 34px 76px minmax(100px, 1fr) auto;
  gap: 8px;
  align-items: center;
  min-height: 42px;
  border: 1px solid rgba(225, 232, 240, 0.6);
  border-radius: 10px;
  padding: 7px 10px;
  background: #ffffff;
  transition: all 0.2s ease;
}

.tree-node--leaf:hover {
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
  border-color: rgba(191, 219, 254, 0.5);
}

.tree-children,
.tree-leaves {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-left: 34px;
  padding: 8px 0 0 18px;
  border-left: 2px solid #dbeafe;
}

.tree-leaves {
  margin-left: 32px;
  border-left-color: #dcfce7;
}

.tree-leaf-rail {
  justify-self: center;
  width: 9px;
  height: 9px;
  border-radius: 99px;
  background: #16a34a;
  box-shadow: 0 0 0 4px #dcfce7;
}

.tree-toggle,
.tree-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  border-radius: 7px;
  background: #fff;
  color: #334155;
  width: 30px;
  height: 30px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.tree-toggle {
  width: 28px;
  height: 28px;
  padding: 0;
  color: #2563eb;
}

.tree-actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.tree-toggle:disabled,
.tree-icon-btn:disabled,
.tree-add-root:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tree-type {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 24px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
}

.tree-type--chapter {
  color: #1d4ed8;
  background: #dbeafe;
}

.tree-type--section {
  color: #0f766e;
  background: #ccfbf1;
}

.tree-type--point {
  color: #15803d;
  background: #dcfce7;
}

.tree-index {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.tree-input {
  width: 100%;
  min-width: 0;
  height: 34px;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 0 8px;
  color: #111827;
  font: inherit;
  font-weight: 700;
  background: transparent;
}

.tree-input:hover {
  border-color: #dbe4f0;
  background: #fff;
}

.tree-input:focus {
  outline: none;
  border-color: #2563eb;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #374151;
}

.compact-field {
  width: 128px;
}

.status-pill {
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: 4px 10px;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 12px;
  font-style: normal;
}

.course-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 290px;
  overflow: auto;
}

.course-row {
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  background: #fff;
  border-radius: 12px;
  padding: 10px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  text-align: left;
  cursor: pointer;
}

.course-row.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.course-row.readonly-row {
  cursor: default;
}

.course-row span,
.resource-review-row div:first-child {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.course-row small,
.course-row em,
.resource-review-row span,
.muted {
  color: #6b7280;
  font-size: 12px;
}

.summary-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summary-grid div {
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  border-radius: 12px;
  padding: 10px;
}

.summary-grid span {
  display: block;
  color: #6b7280;
  font-size: 12px;
}

.summary-grid strong {
  font-size: 22px;
  color: #111827;
}

.graph-tree,
.resource-review-list,
.ability-mapping-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 520px;
  overflow: auto;
}

.graph-node-line {
  min-height: 34px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  border-radius: 12px;
  padding: 7px 9px;
  background: #fff;
}

.graph-node-line span {
  color: #2563eb;
  font-size: 12px;
  white-space: nowrap;
}

.resource-review-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  border-radius: 12px;
  padding: 10px;
}

.resource-review-row a {
  color: #2563eb;
  text-decoration: none;
  overflow-wrap: anywhere;
}

.resource-review-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.resource-filter-tabs {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
}

.resource-filter-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  border: 1px solid #dbe4f0;
  border-radius: 8px;
  padding: 0 10px;
  color: #475569;
  background: #fff;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.resource-filter-tab.active {
  color: #1d4ed8;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.course-runtime-panel {
  display: grid;
  gap: 14px;
}

.runtime-layout {
  display: grid;
  grid-template-columns: 230px minmax(0, 1fr);
  gap: 14px;
  align-items: stretch;
}

.runtime-health,
.runtime-score-card,
.runtime-block {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}

.runtime-health {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 7px;
  padding: 16px;
  border-color: #99f6e4;
  background: #f0fdfa;
}

.runtime-health span,
.runtime-score-card span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.runtime-health strong {
  color: #0f766e;
  font-size: 40px;
  line-height: 1;
}

.runtime-health em,
.runtime-health small,
.runtime-score-card small {
  color: #64748b;
  font-size: 12px;
  font-style: normal;
  line-height: 1.45;
}

.runtime-score-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.runtime-score-card {
  min-height: 100px;
  padding: 12px;
}

.runtime-score-card strong {
  display: block;
  margin-top: 5px;
  color: #0f172a;
  font-size: 24px;
  line-height: 1.1;
}

.runtime-score-card small {
  display: block;
  margin-top: 6px;
}

.runtime-columns {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.runtime-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  padding: 12px;
}

.runtime-block h4 {
  margin: 0 0 2px;
  color: #111827;
  font-size: 14px;
}

.runtime-row {
  display: grid;
  gap: 5px;
  border-top: 1px solid #eef2f7;
  padding-top: 8px;
}

.runtime-row strong {
  color: #111827;
  font-size: 13px;
  line-height: 1.45;
}

.runtime-row span {
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.runtime-evidence-note {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 10px 12px;
  color: #92400e;
  background: #fffbeb;
  font-size: 12px;
}

.course-quiz-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.quiz-definition-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  align-items: start;
}

.quiz-definition-editor,
.quiz-definition-list,
.quiz-question-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quiz-question-row,
.quiz-definition-card {
  border: none;
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
  border-radius: 12px;
  padding: 12px;
  background: #fff;
}

.quiz-question-head,
.quiz-definition-card {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.quiz-question-textarea {
  width: 100%;
  min-height: 120px;
  margin-top: 10px;
  resize: vertical;
  line-height: 1.55;
}

.quiz-answer-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

.quiz-answer-row label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 120px;
  color: #4b5563;
  font-size: 13px;
}

.quiz-definition-card div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.quiz-definition-card span,
.quiz-definition-card small {
  color: #6b7280;
  font-size: 12px;
}

.ability-summary-grid {
  margin: 0 0 14px;
}

.ability-candidate-hint {
  margin: -2px 0 14px;
  color: #4b5f7a;
  font-size: 13px;
  line-height: 1.7;
}

.ability-review-note {
  margin: -2px 0 14px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 10px 12px;
  color: #1e3a8a;
  background: #eff6ff;
  font-size: 13px;
  line-height: 1.65;
}

.ability-runtime-hint {
  margin: 0;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 9px 10px;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 13px;
  line-height: 1.6;
}

.ability-config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.ability-config-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  background: #fff;
}

.ability-config-card strong {
  color: #111827;
}

.ability-form-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.ability-config-card .ability-form-grid {
  grid-template-columns: 1fr;
}

.ability-import-textarea {
  width: 100%;
  min-height: 120px;
  resize: vertical;
  line-height: 1.55;
}

.ability-mapping-create-card {
  margin-bottom: 14px;
}

.ability-gap-draft-card {
  margin-bottom: 14px;
  border-color: #bfdbfe;
  background: #f8fbff;
}

.draft-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.draft-card-head p {
  margin: 4px 0 0;
  color: #4b5f7a;
  font-size: 13px;
  line-height: 1.6;
}

.ability-mapping-reason {
  min-height: 76px;
}

.ability-mapping-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  border: none;
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
  border-radius: 12px;
  padding: 10px;
  background: #fff;
}

.ability-mapping-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ability-mapping-title-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.ability-mapping-title-row strong {
  color: #111827;
}

.ability-status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  border-radius: 999px;
  padding: 0 9px;
  font-size: 12px;
  font-weight: 800;
}

.ability-status-pill.status-confirmed {
  color: #166534;
  background: #dcfce7;
}

.ability-status-pill.status-rejected {
  color: #991b1b;
  background: #fee2e2;
}

.ability-status-pill.status-draft,
.ability-status-pill.status-pending {
  color: #92400e;
  background: #fef3c7;
}

.ability-mapping-meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.ability-mapping-meta-grid div {
  display: grid;
  gap: 3px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 10px;
  background: #f8fafc;
}

.ability-mapping-meta-grid span,
.ability-evidence-line {
  margin: 0;
  color: #6b7280;
  font-size: 12px;
}

.ability-mapping-meta-grid strong {
  color: #111827;
  font-size: 13px;
  line-height: 1.45;
}

.ability-evidence-line {
  line-height: 1.6;
}

.ability-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.ability-chip {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  border-radius: 999px;
  padding: 0 10px;
  color: #0f766e;
  background: #ccfbf1;
  font-size: 12px;
  font-weight: 800;
}

.ghost-btn.tiny {
  min-height: 26px;
  padding: 0 9px;
  font-size: 12px;
  white-space: nowrap;
}

.danger {
  color: #b91c1c;
}

@media (max-width: 980px) {
  .course-twin-grid,
  .course-twin-grid.lower,
  .form-grid,
  .runtime-layout,
  .runtime-columns {
    grid-template-columns: 1fr;
    min-width: 0;
  }

  .course-publish-steps {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .resource-review-row,
  .resource-review-toolbar,
  .ability-mapping-row,
  .ability-config-grid,
  .quiz-definition-layout {
    grid-template-columns: 1fr;
  }

  .resource-review-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .runtime-score-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .tree-row,
  .tree-row--section,
  .tree-node--leaf {
    grid-template-columns: 28px 32px minmax(54px, auto) minmax(0, 1fr);
  }

  .tree-actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }
}

@media (max-width: 700px) {
  .course-publish-steps {
    grid-template-columns: 1fr;
  }

  .course-publish-boundary {
    flex-direction: column;
  }

  .teacher-course-twin-shell,
  .course-twin-grid,
  .course-twin-grid.lower,
  .course-twin-builder,
  .course-twin-side {
    width: 100%;
    max-width: 100%;
    min-width: 0;
    overflow-x: hidden;
  }

  .tree-row,
  .tree-row--section,
  .tree-node--leaf {
    grid-template-columns: 28px 32px minmax(44px, auto) minmax(0, 1fr);
    gap: 6px;
  }

  .tree-node,
  .tree-children,
  .tree-leaves {
    min-width: 0;
    max-width: 100%;
  }

  .tree-leaves {
    margin-left: 12px;
  }

  .tree-index {
    font-size: 11px;
  }

  .tree-input {
    min-width: 0;
  }
}
</style>
