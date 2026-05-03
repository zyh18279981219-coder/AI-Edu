// 页面切换
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        
        // 更新导航激活状态
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        
        // 切换页面内容
        const target = link.getAttribute('href').substring(1);
        document.querySelectorAll('.page-content').forEach(page => {
            page.classList.remove('active');
            page.style.display = 'none';
        });
        
        const targetPage = document.getElementById(`page-${target}`);
        if (targetPage) {
            targetPage.classList.add('active');
            targetPage.style.display = 'block';
        }
    });
});

// 中间内容区Tab切换（学习中心）
document.querySelectorAll('.main-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const contentType = btn.getAttribute('data-content');
        
        // 更新Tab激活状态
        document.querySelectorAll('.main-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // 切换内容视图
        document.querySelectorAll('.main-content-view').forEach(view => {
            view.classList.remove('active');
            view.style.display = 'none';
        });
        
        const targetView = document.getElementById(`content-${contentType}`);
        if (targetView) {
            targetView.classList.add('active');
            targetView.style.display = 'flex';
        }
    });
});

// 内容查看器Tab切换（PDF、视频、测验等）
document.querySelectorAll('.viewer-tab').forEach(btn => {
    btn.addEventListener('click', () => {
        const viewType = btn.getAttribute('data-view');
        
        // 更新Tab激活状态
        document.querySelectorAll('.viewer-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // 切换视图面板
        document.querySelectorAll('.view-panel').forEach(panel => {
            panel.classList.remove('active');
            panel.style.display = 'none';
        });
        
        const targetPanel = document.getElementById(`view-${viewType}`);
        if (targetPanel) {
            targetPanel.classList.add('active');
            targetPanel.style.display = 'block';
        }
    });
});

// 目录树折叠/展开
document.querySelectorAll('.chapter-header, .section-header').forEach(header => {
    header.addEventListener('click', (e) => {
        const parent = header.parentElement;
        parent.classList.toggle('collapsed');
        
        const toggle = header.querySelector('.toggle');
        if (toggle) {
            toggle.textContent = parent.classList.contains('collapsed') ? '▶' : '▼';
        }
    });
});

// 目录节点点击
document.querySelectorAll('.catalog-node').forEach(node => {
    node.addEventListener('click', () => {
        document.querySelectorAll('.catalog-node').forEach(n => n.classList.remove('active'));
        node.classList.add('active');
        
        // 模拟加载内容
        console.log('切换到知识点:', node.querySelector('.node-title').textContent);
    });
});

// 聊天发送
const chatInput = document.querySelector('.chat-input');
const btnSend = document.querySelector('.btn-send');
const chatMessages = document.querySelector('.chat-messages');

function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    // 添加用户消息
    const userMsg = document.createElement('div');
    userMsg.className = 'message user-message';
    userMsg.innerHTML = `
        <div class="message-content">
            <p>${message}</p>
        </div>
        <div class="message-avatar">👤</div>
    `;
    chatMessages.appendChild(userMsg);
    
    // 清空输入框
    chatInput.value = '';
    
    // 滚动到底部
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // 模拟智能体回复
    setTimeout(() => {
        const agentMsg = document.createElement('div');
        agentMsg.className = 'message agent-message';
        agentMsg.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <p>我理解你的问题了。让我为你推荐一些相关资源...</p>
            </div>
        `;
        chatMessages.appendChild(agentMsg);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 1000);
}

btnSend.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// 推荐资源点击
document.querySelectorAll('.btn-rec').forEach(btn => {
    btn.addEventListener('click', (e) => {
        if (btn.disabled) return;
        
        const item = btn.closest('.recommendation-item');
        const title = item.querySelector('.rec-title').textContent;
        
        console.log('打开资源:', title);
        alert(`正在加载资源: ${title}`);
    });
});

// 数据页面标签切换
document.querySelectorAll('.data-tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.data-tabs .tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        console.log('切换到:', btn.textContent);
    });
});

// 作业卡片按钮
document.querySelectorAll('.homework-card button').forEach(btn => {
    btn.addEventListener('click', () => {
        const card = btn.closest('.homework-card');
        const title = card.querySelector('h3').textContent;
        
        console.log('操作作业:', title);
        alert(`操作: ${title}`);
    });
});

// 内容操作按钮
document.querySelectorAll('.content-footer button').forEach(btn => {
    btn.addEventListener('click', () => {
        console.log('点击:', btn.textContent);
        alert(`功能: ${btn.textContent}`);
    });
});

// 笔记保存
const btnSaveNote = document.querySelector('.btn-save-note');
if (btnSaveNote) {
    btnSaveNote.addEventListener('click', () => {
        const notes = document.querySelector('.notes-input').value;
        console.log('保存笔记:', notes);
        alert('笔记已保存！');
    });
}


// ==================== 5E智能体流程 ====================
let currentStage = 'engagement';

// 阶段1: 开始探索
function startExploration() {
    currentStage = 'exploration';
    updateStageBadge('exploration', 'Exploration');
    updateStageTip('探索实践');
    
    addUserMessage('开始学习');
    
    setTimeout(() => {
        addAgentHTML(`
            <div class="msg agent-msg">
                <div class="msg-avatar">🤖</div>
                <div class="msg-bubble">
                    <p>太好了！让我们开始探索<strong>「大数据生命周期」</strong>。</p>
                    <p>我为你准备了以下学习资源：</p>
                </div>
            </div>
            <div class="msg agent-msg">
                <div class="resource-card" onclick="viewPDF()">
                    <div class="resource-icon">📄</div>
                    <div class="resource-info">
                        <div class="resource-title">大数据生命周期详解.pdf</div>
                        <div class="resource-meta">15页 · 预计10分钟</div>
                    </div>
                </div>
                <div class="resource-card" onclick="viewVideo()">
                    <div class="resource-icon">🎥</div>
                    <div class="resource-info">
                        <div class="resource-title">大数据生命周期讲解视频</div>
                        <div class="resource-meta">12:35 · 高清</div>
                    </div>
                </div>
            </div>
            <div class="msg action-msg">
                <button class="action-btn-inline success" onclick="finishExploration()">✅ 我已学习完成</button>
                <button class="action-btn-inline secondary" onclick="sendCustomMsg('我有问题')">💬 我有问题</button>
            </div>
        `);
    }, 800);
}

// 阶段2: 完成探索，进入理解纠错
function finishExploration() {
    currentStage = 'explanation';
    updateStageBadge('explanation', 'Explanation');
    updateStageTip('理解纠错');
    updateMasteryTip('当前掌握度: 40%');
    
    addUserMessage('我已学习完成');
    
    setTimeout(() => {
        addAgentHTML(`
            <div class="msg agent-msg">
                <div class="msg-avatar">🤖</div>
                <div class="msg-bubble">
                    <p>很好！现在让我检查一下你的理解。</p>
                </div>
            </div>
            <div class="msg agent-msg">
                <div class="question-card">
                    <div class="question-title">💭 思考题</div>
                    <div class="question-text">
                        请用自己的话描述：大数据生命周期包括哪几个主要阶段？
                    </div>
                    <textarea class="answer-input" id="answer-input" placeholder="在这里输入你的理解..."></textarea>
                </div>
            </div>
            <div class="msg action-msg">
                <button class="action-btn-inline" onclick="submitAnswer()">📤 提交答案</button>
            </div>
        `);
    }, 800);
}

// 提交答案
function submitAnswer() {
    const answerInput = document.getElementById('answer-input');
    const answer = answerInput ? answerInput.value.trim() : '';
    
    if (!answer) {
        alert('请先输入你的答案');
        return;
    }
    
    addUserMessage(answer);
    
    setTimeout(() => {
        addAgentHTML(`
            <div class="msg agent-msg">
                <div class="msg-avatar">🤖</div>
                <div class="msg-bubble">
                    <div class="feedback-card feedback-correct">
                        <div class="feedback-title">✅ 理解正确！</div>
                        <div class="feedback-text">
                            你准确地把握了大数据生命周期的核心阶段：
                            <ul>
                                <li><strong>数据采集</strong>：从各种数据源收集原始数据</li>
                                <li><strong>数据存储</strong>：将数据存储在分布式系统中</li>
                                <li><strong>数据处理</strong>：清洗、转换和计算数据</li>
                                <li><strong>数据分析</strong>：从数据中提取有价值的信息</li>
                                <li><strong>数据应用</strong>：将分析结果应用到实际业务</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            <div class="msg action-msg">
                <button class="action-btn-inline" onclick="startElaboration()">➡️ 继续学习</button>
            </div>
        `);
        updateMasteryTip('当前掌握度: 65%');
    }, 1500);
}

// 阶段3: 拓展应用
function startElaboration() {
    currentStage = 'elaboration';
    updateStageBadge('elaboration', 'Elaboration');
    updateStageTip('拓展应用');
    
    addUserMessage('继续学习');
    
    setTimeout(() => {
        addAgentHTML(`
            <div class="msg agent-msg">
                <div class="msg-avatar">🤖</div>
                <div class="msg-bubble">
                    <p>太棒了！现在让我们看看实际应用。</p>
                    <p>我帮你搜索了相关的行业岗位：</p>
                </div>
            </div>
            <div class="msg action-msg">
                <button class="action-btn-inline warning" onclick="searchIndustry()">💼 查看相关岗位</button>
                <button class="action-btn-inline secondary" onclick="finishElaboration()">➡️ 跳过，进入测验</button>
            </div>
        `);
    }, 800);
}

// 跳转到行业资讯
function searchIndustry() {
    addUserMessage('查看相关岗位');
    
    setTimeout(() => {
        addAgentMessage('正在为你跳转到行业资讯页面，搜索关键词已自动填充...');
        
        setTimeout(() => {
            document.querySelector('.nav-link[href="#industry"]').click();
        }, 1500);
    }, 500);
}

// 阶段4: 进入测验
function finishElaboration() {
    currentStage = 'evaluation';
    updateStageBadge('evaluation', 'Evaluation');
    updateStageTip('评估测验');
    updateMasteryTip('当前掌握度: 80%');
    
    addUserMessage('进入测验');
    
    setTimeout(() => {
        addAgentHTML(`
            <div class="msg agent-msg">
                <div class="msg-avatar">🤖</div>
                <div class="msg-bubble">
                    <p>🎉 恭喜！现在让我们通过测验检验学习成果。</p>
                </div>
            </div>
            <div class="msg action-msg">
                <button class="action-btn-inline" onclick="startQuiz()">📝 开始测验</button>
            </div>
        `);
    }, 800);
}

// 开始测验
function startQuiz() {
    addUserMessage('开始测验');
    
    setTimeout(() => {
        addAgentMessage('正在为你跳转到测验页面...');
        
        setTimeout(() => {
            document.querySelector('.viewer-tab[data-view="quiz"]').click();
            updateMasteryTip('当前掌握度: 90%');
        }, 1500);
    }, 500);
}

// 辅助函数
function updateStageBadge(stage, text) {
    const badge = document.getElementById('stage-badge');
    if (badge) {
        badge.className = 'stage-badge stage-' + stage;
        badge.textContent = text;
    }
}

function updateStageTip(text) {
    const tip = document.getElementById('current-stage-tip');
    if (tip) {
        tip.textContent = '当前阶段: ' + text;
    }
}

function updateMasteryTip(text) {
    const tip = document.getElementById('mastery-tip');
    if (tip) {
        tip.textContent = text;
    }
}

function addUserMessage(text) {
    const messagesContainer = document.getElementById('messages');
    messagesContainer.innerHTML += `
        <div class="msg user-msg">
            <div class="msg-bubble"><p>${text}</p></div>
            <div class="msg-avatar">👤</div>
        </div>
    `;
    scrollToBottom();
}

function addAgentMessage(text) {
    const messagesContainer = document.getElementById('messages');
    messagesContainer.innerHTML += `
        <div class="msg agent-msg">
            <div class="msg-avatar">🤖</div>
            <div class="msg-bubble"><p>${text}</p></div>
        </div>
    `;
    scrollToBottom();
}

function addAgentHTML(html) {
    const messagesContainer = document.getElementById('messages');
    messagesContainer.innerHTML += html;
    scrollToBottom();
}

function scrollToBottom() {
    const messagesContainer = document.getElementById('messages');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

function viewPDF() {
    document.querySelector('.viewer-tab[data-view="pdf"]').click();
    addAgentMessage('已为你打开PDF文档，请仔细阅读。');
}

function viewVideo() {
    document.querySelector('.viewer-tab[data-view="video"]').click();
    addAgentMessage('已为你打开视频讲解，建议完整观看。');
}

function sendCustomMsg(text) {
    addUserMessage(text);
    setTimeout(() => {
        addAgentMessage('我理解你的问题。如果在学习过程中遇到困难，随时告诉我！');
    }, 800);
}

function handleEnter(event) {
    if (event.key === 'Enter') {
        sendMsg();
    }
}

function sendMsg() {
    const input = document.getElementById('msg-input');
    const message = input ? input.value.trim() : '';
    
    if (!message) return;
    
    addUserMessage(message);
    input.value = '';
    
    setTimeout(() => {
        addAgentMessage('我理解你的问题。如果在学习过程中遇到困难，随时告诉我！');
    }, 800);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ 页面加载完成');
    
    // 确保首页显示
    const homePage = document.getElementById('page-home');
    if (homePage) {
        homePage.classList.add('active');
        homePage.style.display = 'block';
    }
    
    // 确保其他页面隐藏
    ['learning-center', 'homework', 'industry', 'profile'].forEach(pageId => {
        const page = document.getElementById(`page-${pageId}`);
        if (page) {
            page.classList.remove('active');
            page.style.display = 'none';
        }
    });
    
    // 确保首页导航链接是激活状态
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === '#home') {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
    
    console.log('✅ AI-Education 学生端原型已加载');
    console.log('💡 这是一个静态原型，用于展示UI设计和交互流程');
});
