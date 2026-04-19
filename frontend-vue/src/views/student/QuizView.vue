<template>
  <div class="quiz-shell-vue">
    <PageHero
      eyebrow="Quiz"
      :title="quizTopic ? `${quizTopic} 测验` : '在线测验'"
      description="基于当前知识点自动生成测验题，完成后可以查看结果、生成总结，并衔接后续学习计划。"
      :badges="heroBadges"
      tone="learning"
    >
      <template #actions>
        <RouterLink class="ghost-btn" :to="returnRoute">返回课程</RouterLink>
      </template>
    </PageHero>

    <section v-if="loading" class="card-panel quiz-loading-card">
      <div class="quiz-loading-spinner"></div>
      <p>正在生成测验题目，请稍候...</p>
    </section>

    <section v-else-if="error" class="state-card error-state">
      <h2>测验加载失败</h2>
      <p>{{ error }}</p>
      <RouterLink class="ghost-btn" :to="returnRoute">返回课程</RouterLink>
    </section>

    <template v-else-if="currentQuestion && !finished">
      <section class="card-panel quiz-progress-card">
        <div class="quiz-progress-top">
          <div>
            <strong>答题进度</strong>
            <span>{{ currentStep }} / {{ totalQuestions }}</span>
          </div>
          <div class="quiz-progress-score">当前得分 {{ correctCount }} / {{ answeredCount }}</div>
        </div>
        <div class="progress-line"><span :style="{ width: `${progressPercent}%` }"></span></div>
      </section>

      <section class="quiz-layout-vue">
        <article class="card-panel quiz-question-card">
          <div class="quiz-question-head">
            <span class="pill">{{ currentQuestion.topic }}</span>
            <span class="muted">单项选择</span>
          </div>
          <h2>{{ parsedQuestion.stem || currentQuestion.question }}</h2>

          <div v-if="parsedQuestion.options.length" class="quiz-option-list">
            <button
              v-for="option in parsedQuestion.options"
              :key="option.key"
              type="button"
              class="quiz-option-btn"
              :class="optionStateClass(option.key)"
              :disabled="submitting || !!lastFeedback"
              @click="submitChoice(option.key)"
            >
              <span class="quiz-option-key">{{ option.key.toUpperCase() }}</span>
              <span class="quiz-option-text">{{ option.text }}</span>
            </button>
          </div>
          <div v-else class="list-card pre-wrap">{{ currentQuestion.question }}</div>

          <div v-if="lastFeedback" class="quiz-feedback" :class="lastFeedback.correct ? 'correct' : 'incorrect'">
            <strong>{{ lastFeedback.correct ? "回答正确" : "回答错误" }}</strong>
            <p>正确答案：{{ lastFeedback.correctAnswer.toUpperCase() }}</p>
          </div>

          <div class="quiz-actions">
            <button
              v-if="lastFeedback"
              type="button"
              class="primary-link button-like"
              @click="goNext"
            >
              {{ isLastQuestion ? "查看结果" : "下一题" }}
            </button>
          </div>
        </article>

        <aside class="quiz-side-vue">
          <article class="card-panel">
            <div class="section-head">
              <h2>本次测验</h2>
            </div>
            <div class="stack-list">
              <div class="list-card">
                <div class="list-title">题目数量</div>
                <div class="list-meta">{{ totalQuestions }} 题</div>
              </div>
              <div class="list-card">
                <div class="list-title">知识点主题</div>
                <div class="list-meta">{{ quizTopic }}</div>
              </div>
              <div class="list-card">
                <div class="list-title">知识检索</div>
                <div class="list-meta">{{ usedRetriever ? "已结合课程资料" : "未使用课程资料" }}</div>
              </div>
            </div>
          </article>
        </aside>
      </section>
    </template>

    <template v-else-if="finished">
      <section class="quiz-result-grid">
        <article class="card-panel quiz-result-card">
          <div class="quiz-result-icon">{{ resultEmoji }}</div>
          <h2>测验完成</h2>
          <div class="quiz-result-score">{{ correctCount }} / {{ totalQuestions }}</div>
          <p class="quiz-result-text">{{ resultMessage }}</p>
          <div class="quiz-result-actions">
            <button type="button" class="primary-link button-like" :disabled="summaryLoading" @click="loadSummary">
              {{ summaryLoading ? "生成中..." : "生成测验总结" }}
            </button>
            <button type="button" class="ghost-btn" :disabled="planLoading" @click="loadPlan">
              {{ planLoading ? "生成中..." : "生成学习计划" }}
            </button>
            <button type="button" class="ghost-btn" @click="restartQuiz">重新开始</button>
            <RouterLink class="ghost-btn" :to="returnRoute">返回课程</RouterLink>
          </div>
        </article>

        <article class="card-panel quiz-analysis-card">
          <div class="section-head">
            <h2>答题记录</h2>
            <span class="muted">{{ answerRecords.length }} 条记录</span>
          </div>
          <div class="stack-list">
            <div v-for="(record, index) in answerRecords" :key="`${record.question}-${index}`" class="list-card">
              <div class="list-title">{{ index + 1 }}. {{ record.stem || record.question }}</div>
              <div class="list-meta">
                你的答案 {{ record.selected.toUpperCase() }} · 正确答案 {{ record.correctAnswer.toUpperCase() }}
              </div>
            </div>
          </div>
        </article>
      </section>

      <section class="detail-grid quiz-detail-grid">
        <article class="card-panel">
          <div class="section-head">
            <h2>测验总结</h2>
          </div>
          <div class="assistant-output pre-wrap" :class="{ 'error-state': !!summaryError }">
            {{ summaryError || quizSummary || "点击上方按钮后会在这里生成测验总结。" }}
          </div>
        </article>

        <article class="card-panel">
          <div class="section-head">
            <h2>学习计划</h2>
          </div>
          <div v-if="planError" class="assistant-output error-state">{{ planError }}</div>
          <div v-else-if="generatedPlan.length" class="stack-list">
            <div v-for="entry in generatedPlan" :key="`${entry.date}-${entry.topic}`" class="list-card">
              <div class="list-title">{{ entry.date }} · {{ entry.topic }}</div>
              <div class="list-meta">{{ entry.priority }}<span v-if="entry.deadline"> · 截止 {{ entry.deadline }}</span></div>
              <ul class="material-list">
                <li v-for="material in entry.materials" :key="material">{{ material }}</li>
              </ul>
            </div>
          </div>
          <div v-else class="assistant-output">点击上方按钮后会基于测验结果生成学习计划。</div>
        </article>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import PageHero from "../../components/ui/PageHero.vue";
import {
  answerQuiz,
  completeQuiz,
  generateQuizSummary,
  startQuiz,
  type QuizQuestion,
  type QuizState,
} from "../../api/client";
import {LearningPlanEntry} from "../../types/student";
import {fetchCurrentUser} from "../../api/login";
import {generateLearningPlanFromQuiz} from "../../api/student";

type AnswerRecord = {
  type: "choice";
  question: string;
  stem: string;
  selected: string;
  correctAnswer: string;
  isCorrect: boolean;
};

const route = useRoute();
const router = useRouter();

const loading = ref(true);
const submitting = ref(false);
const summaryLoading = ref(false);
const planLoading = ref(false);
const error = ref("");
const quizTopic = ref("");
const currentQuestion = ref<QuizQuestion | null>(null);
const quizState = ref<QuizState | null>(null);
const usedRetriever = ref(false);
const finished = ref(false);
const answerRecords = ref<AnswerRecord[]>([]);
const lastFeedback = ref<{ selected: string; correct: boolean; correctAnswer: string } | null>(null);
const pendingNextQuestion = ref<QuizQuestion | null>(null);
const resultText = ref("");
const quizSummary = ref("");
const summaryError = ref("");
const generatedPlan = ref<LearningPlanEntry[]>([]);
const planError = ref("");
const currentUsername = ref("");

const totalQuestions = computed(() => quizState.value?.questions.length ?? 0);
const currentStep = computed(() => Math.min((quizState.value?.index ?? 0) + 1, totalQuestions.value || 1));
const answeredCount = computed(() => answerRecords.value.length);
const correctCount = computed(() => answerRecords.value.filter((item) => item.isCorrect).length);
const progressPercent = computed(() => totalQuestions.value ? (currentStep.value / totalQuestions.value) * 100 : 0);
const isLastQuestion = computed(() => (quizState.value?.index ?? 0) >= totalQuestions.value - 1);

const returnRoute = computed(() => {
  const node = typeof route.query.node === "string" ? route.query.node : quizTopic.value;
  return node ? { path: "/student/course-content", query: { node } } : { path: "/student/course-content" };
});

const heroBadges = computed(() => [
  `主题 ${quizTopic.value || "未指定"}`,
  `题目 ${totalQuestions.value}`,
  `得分 ${correctCount.value}/${Math.max(answeredCount.value, 0)}`,
]);

const parsedQuestion = computed(() => parseQuestion(currentQuestion.value?.question ?? ""));

const resultEmoji = computed(() => {
  const percent = totalQuestions.value ? (correctCount.value / totalQuestions.value) * 100 : 0;
  if (percent >= 90) return "冠军";
  if (percent >= 70) return "优秀";
  if (percent >= 60) return "及格";
  return "待提升";
});

const resultMessage = computed(() => {
  if (resultText.value) return resultText.value;
  const percent = totalQuestions.value ? (correctCount.value / totalQuestions.value) * 100 : 0;
  if (percent >= 90) return "表现非常出色，当前知识点掌握得很扎实。";
  if (percent >= 70) return "整体不错，再补一补错题相关知识点会更稳。";
  if (percent >= 60) return "已经达到及格水平，但还有一些关键点需要继续巩固。";
  return "这次暴露出一些薄弱点，建议结合总结和学习计划继续强化。";
});

function parseQuestion(questionText: string) {
  const lines = questionText
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const optionRegex = /^([A-Da-d])[\.\):：\s]*(.+)$/;
  const options: Array<{ key: string; text: string }> = [];
  const stemLines: string[] = [];

  for (const line of lines) {
    const match = line.match(optionRegex);
    if (match) {
      options.push({ key: match[1].toLowerCase(), text: match[2] });
    } else {
      stemLines.push(line);
    }
  }

  return {
    stem: stemLines.join("\n"),
    options,
  };
}

function optionStateClass(key: string) {
  if (!lastFeedback.value) return "";
  if (key === lastFeedback.value.correctAnswer) return "correct";
  if (key === lastFeedback.value.selected && !lastFeedback.value.correct) return "incorrect";
  return "disabled";
}

async function initQuiz() {
  loading.value = true;
  error.value = "";
  finished.value = false;
  answerRecords.value = [];
  lastFeedback.value = null;
  pendingNextQuestion.value = null;
  resultText.value = "";
  quizSummary.value = "";
  summaryError.value = "";
  generatedPlan.value = [];
  planError.value = "";

  try {
    const user = await fetchCurrentUser();
    currentUsername.value = String(user.user_data["stu_name"] ?? user.user_data["name"] ?? user.username ?? "");
  } catch {
    currentUsername.value = "";
  }

  try {
    const topic = typeof route.query.topic === "string" ? route.query.topic : typeof route.query.node === "string" ? route.query.node : "";
    if (!topic) {
      throw new Error("缺少测验主题，无法开始测验");
    }
    quizTopic.value = topic;
    const result = await startQuiz({ subject: topic, lang_choice: "中文" });
    currentQuestion.value = result.question;
    quizState.value = result.state;
    usedRetriever.value = !!result.used_retriever;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "测验生成失败";
  } finally {
    loading.value = false;
  }
}

async function submitChoice(choice: string) {
  if (!quizState.value || !currentQuestion.value || submitting.value) return;
  submitting.value = true;
  try {
    const current = currentQuestion.value;
    const response = await answerQuiz({ choice, state: quizState.value });
    quizState.value = response.state;
    answerRecords.value.push({
      type: "choice",
      question: current.question,
      stem: parseQuestion(current.question).stem,
      selected: choice,
      correctAnswer: response.correct_answer ?? current.correct ?? "?",
      isCorrect: !!response.is_correct,
    });
    lastFeedback.value = {
      selected: choice,
      correct: !!response.is_correct,
      correctAnswer: response.correct_answer ?? current.correct ?? "?",
    };
    if (response.finished) {
      pendingNextQuestion.value = null;
      finished.value = true;
      currentQuestion.value = null;
      resultText.value = response.results ?? "";
      if (quizTopic.value) {
        await completeQuiz({
          node_name: quizTopic.value,
          score: correctCount.value,
          total: totalQuestions.value,
        }).catch(() => undefined);
      }
    } else {
      pendingNextQuestion.value = response.next_question ?? null;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "提交答案失败";
  } finally {
    submitting.value = false;
  }
}

function goNext() {
  if (!pendingNextQuestion.value) {
    finished.value = true;
    currentQuestion.value = null;
    return;
  }
  currentQuestion.value = pendingNextQuestion.value;
  pendingNextQuestion.value = null;
  lastFeedback.value = null;
}

async function loadSummary() {
  if (!quizState.value) return;
  summaryLoading.value = true;
  summaryError.value = "";
  try {
    const { summary } = await generateQuizSummary({
      topic: quizTopic.value,
      score: correctCount.value,
      total: totalQuestions.value,
      user_answers: answerRecords.value.map((item) => ({
        type: item.type,
        selected: item.selected,
        correct_answer: item.correctAnswer,
        is_correct: item.isCorrect,
      })),
      questions: quizState.value.questions,
    });
    quizSummary.value = summary;
  } catch (err) {
    summaryError.value = err instanceof Error ? err.message : "测验总结生成失败";
  } finally {
    summaryLoading.value = false;
  }
}

async function loadPlan() {
  if (!quizState.value) return;
  planLoading.value = true;
  planError.value = "";
  try {
    const data = await generateLearningPlanFromQuiz({
      name: currentUsername.value || "student",
      state: quizState.value,
      lang_choice: "中文",
    });
    generatedPlan.value = data.plan;
  } catch (err) {
    planError.value = err instanceof Error ? err.message : "学习计划生成失败";
  } finally {
    planLoading.value = false;
  }
}

function restartQuiz() {
  void initQuiz();
}

onMounted(() => {
  void initQuiz();
});
</script>
