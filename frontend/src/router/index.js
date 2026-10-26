import { createRouter, createWebHistory } from 'vue-router'
import Login from '../components/Login.vue'
import Home from '../components/Home.vue'
import Dashboard from '../components/Dashboard.vue'
import Analytics from '../components/Analytics.vue'
import Budget from '../components/Budget.vue'
import Predict from '../components/Predict.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: Login },
  { path: '/dashboard', redirect: '/home/dashboard' },
  { path: '/analytics', redirect: '/home/analytics' },
  { path: '/budget', redirect: '/home/budget' },
  { path: '/predict', redirect: '/home/predict' },
  {
    path: '/home',
    component: Home,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: 'dashboard' },
      { path: 'dashboard', component: Dashboard },
      { path: 'analytics', component: Analytics },
      { path: 'budget', component: Budget },
      { path: 'predict', component: Predict },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !localStorage.getItem('isLoggedIn')) {
    next('/login')
  } else {
    next()
  }
})

export default router
