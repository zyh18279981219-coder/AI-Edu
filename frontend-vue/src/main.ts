import {createApp} from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles/main.css";
import i18n from "./locale/index";

const app = createApp(App);

app.use(router)
    .use(i18n);

app.mount("#app");
