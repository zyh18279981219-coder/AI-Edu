import layout from "./en/layout";
import login from "./en/login";
import home from "./en/student/home";

export default {
    login:login,
    layout: layout,
    student: {
        home: home,
        myLearning: {
            createNewPlan: 'Create a new plan',

            learningPlan: 'Learning plan',
            learningPlanDescription: 'Historical plans and current plans will be summarized together.',
            pathNode: 'Path node',
            pathNodeDescription: 'Personalized path nodes generated based on weak knowledge points.',
            language: 'Optional languages',
            languageDescription: 'Number of output languages that can be selected when creating a new plan.',
            plansThisMonth: 'This month\'s plans',
            plansThisMonthDescription: 'Number of learning tasks already scheduled in the current monthly calendar.',

            calendar: 'Learning Calendar',
            calendarPlans: 'This Month\'s plans',
        }
    }
}