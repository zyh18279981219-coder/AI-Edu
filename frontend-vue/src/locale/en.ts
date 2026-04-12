import layout from "./en/layout";
import login from "./en/login";
import home from "./en/student/home";
import myLearning from "./en/student/myLearning";
import profile from "./en/student/profile";
import studentTwin from "./en/student/studentTwin";
import industryIntelligence from "./en/student/industryIntelligence";

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