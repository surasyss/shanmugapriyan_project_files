import Vue from 'vue'

import store from "../store";
import DashboardContainer from "./DashboardContainer";
import { BootstrapVue, IconsPlugin, LayoutPlugin } from 'bootstrap-vue'
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'
// Install BootstrapVue
Vue.use(BootstrapVue)
// Optionally install the BootstrapVue icon components plugin
Vue.use(IconsPlugin)
Vue.use(LayoutPlugin)


global.browser = require('webextension-polyfill')
Vue.prototype.$browser = global.browser
Vue.config.productionTip = false
/* eslint-disable no-new */
export default new Vue({
    store,
    render: h => h(DashboardContainer)
}).$mount('#dashboard')
console.log("dashboard js loaded")

