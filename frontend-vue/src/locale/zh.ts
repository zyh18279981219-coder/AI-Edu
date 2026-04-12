import login from "./zh/login";
import layout from "./zh/layout";
import home from "./zh/student/home";
import myLearning from "./zh/student/myLearning";
import profile from "./zh/student/profile";
import studentTwin from "./zh/student/studentTwin";
import industryIntelligence from "./zh/student/industryIntelligence";

export default {
    login: login,
    layout: layout,
    student: {
        home: home,
        myLearning: myLearning,
        studentTwin:studentTwin,
        industryIntelligence:industryIntelligence,
        profile:profile
    }
}