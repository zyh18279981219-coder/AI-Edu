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

// 生成AI建议
function generateAISuggestions() {
    const section = document.getElementById('ai-suggestions-section');
    const teachingSuggestions = document.getElementById('teaching-suggestions');
    const interventionSuggestions = document.getElementById('intervention-suggestions');
    
    // 显示加载状态
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '🤖 生成中...';
    btn.disabled = true;
    
    // 模拟AI生成（实际应该调用后端API）
    setTimeout(() => {
        // 教学策略建议
        teachingSuggestions.innerHTML = `
            <div class="suggestion-item">
                <div class="suggestion-icon">💡</div>
                <div class="suggestion-content">
                    <div class="suggestion-title">增加评估多样性</div>
                    <div class="suggestion-desc">建议在现有测验基础上，增加项目式评估和同伴互评，提升评估维度得分。可以尝试每章设置1个小项目，让学生实践所学知识。</div>
                </div>
            </div>
            <div class="suggestion-item">
                <div class="suggestion-icon">📚</div>
                <div class="suggestion-content">
                    <div class="suggestion-title">优化资源迭代频率</div>
                    <div class="suggestion-desc">建议每周复盘教学资源使用效果，根据学生反馈及时更新。特别关注学生掌握度低的知识点，补充更多案例和练习。</div>
                </div>
            </div>
            <div class="suggestion-item">
                <div class="suggestion-icon">🎯</div>
                <div class="suggestion-content">
                    <div class="suggestion-title">提升AI协作执行率</div>
                    <div class="suggestion-desc">当前AI推荐动作执行率为70%，建议优先执行针对薄弱知识点的干预建议，可以显著提升班级整体掌握度。</div>
                </div>
            </div>
        `;
        
        // 干预策略建议
        interventionSuggestions.innerHTML = `
            <div class="suggestion-item">
                <div class="suggestion-icon">⚠️</div>
                <div class="suggestion-content">
                    <div class="suggestion-title">评估维度低于阈值触发</div>
                    <div class="suggestion-desc">当评估维度分值低于70分时，系统将自动推送改进清单、最佳实践案例，并在下周跟踪改进幅度。</div>
                </div>
            </div>
            <div class="suggestion-item">
                <div class="suggestion-icon">📊</div>
                <div class="suggestion-content">
                    <div class="suggestion-title">学生掌握度预警</div>
                    <div class="suggestion-desc">当班级平均掌握度连续2周下降时，建议组织专题答疑，并为薄弱学生生成个性化学习计划。</div>
                </div>
            </div>
            <div class="suggestion-item">
                <div class="suggestion-icon">🎓</div>
                <div class="suggestion-content">
                    <div class="suggestion-title">知识点掌握度监控</div>
                    <div class="suggestion-desc">当某个知识点班级平均掌握度低于60%时，自动触发教学干预：推送补充资料、组织小组讨论、布置针对性作业。</div>
                </div>
            </div>
        `;
        
        // 显示建议区域
        section.style.display = 'block';
        section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        // 恢复按钮状态
        btn.textContent = '✅ 已生成';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
    }, 1500);
}

// 干预按钮点击
document.querySelectorAll('.btn-intervene, .btn-action').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const item = e.target.closest('.student-alert-item, .ranking-item');
        if (item) {
            const studentName = item.querySelector('.student-name, .rank-name')?.textContent;
            alert(`正在为 ${studentName} 生成干预方案...\n\n建议操作：\n1. 布置针对性作业\n2. 推送补充学习资料\n3. 安排一对一辅导`);
        }
    });
});

// 学生卡片按钮
document.querySelectorAll('.student-card button').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const card = e.target.closest('.student-card');
        const studentName = card.querySelector('.student-name-large')?.textContent;
        const action = e.target.textContent;
        
        if (action.includes('详情')) {
            alert(`查看 ${studentName} 的详细学习数据...\n\n包括：\n- 知识点掌握情况\n- 学习轨迹\n- 作业完成情况\n- 测验成绩分析`);
        } else if (action.includes('作业')) {
            alert(`为 ${studentName} 布置个性化作业...\n\n系统建议：\n- 针对薄弱知识点\n- 难度适中\n- 包含实践环节`);
        } else {
            alert(`${action} ${studentName}`);
        }
    });
});

// 资源操作按钮
document.querySelectorAll('.resource-item .btn-icon').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const item = e.target.closest('.resource-item');
        const resourceName = item.querySelector('.resource-name')?.textContent;
        const action = e.target.getAttribute('title');
        
        console.log(`${action}: ${resourceName}`);
        alert(`${action}: ${resourceName}`);
    });
});

// 作业批改按钮
document.querySelectorAll('.homework-review-item button').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const item = e.target.closest('.homework-review-item');
        const studentName = item.querySelector('.hw-student-name')?.textContent;
        const hwTitle = item.querySelector('.hw-assignment-title')?.textContent;
        const action = e.target.textContent;
        
        if (action.includes('详情')) {
            alert(`查看作业详情：\n学生：${studentName}\n作业：${hwTitle}`);
        } else if (action.includes('批改')) {
            alert(`开始批改作业：\n学生：${studentName}\n作业：${hwTitle}\n\n批改功能：\n- 评分\n- 批注\n- 反馈建议\n- AI辅助评分`);
        }
    });
});

// 标签页切换
document.querySelectorAll('.resource-tab, .hw-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
        const parent = e.target.parentElement;
        parent.querySelectorAll('.resource-tab, .hw-tab').forEach(t => t.classList.remove('active'));
        e.target.classList.add('active');
        
        console.log('切换到:', e.target.textContent);
    });
});

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ 教师端页面加载完成');
    
    // 确保数据看板默认显示
    const dashboardPage = document.getElementById('page-dashboard');
    if (dashboardPage) {
        dashboardPage.classList.add('active');
        dashboardPage.style.display = 'block';
    }
    
    // 确保其他页面隐藏
    ['students', 'resources', 'homework', 'profile'].forEach(pageId => {
        const page = document.getElementById(`page-${pageId}`);
        if (page) {
            page.classList.remove('active');
            page.style.display = 'none';
        }
    });
    
    // 确保数据看板导航链接是激活状态
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === '#dashboard') {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
    
    console.log('💡 这是一个静态原型，用于展示教师端UI设计和交互流程');
});
