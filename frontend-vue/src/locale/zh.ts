import login from "./zh/login";
import layout from "./zh/layout";
import home from "./zh/student/home";
import myLearning from "./zh/student/myLearning";
import profile from "./zh/student/profile";
import studentTwin from "./zh/student/studentTwin";

export default {
    login: login,
    layout: layout,
    student: {
        home: home,
        myLearning: myLearning,
        studentTwin:studentTwin,
        profile:profile
    }
}