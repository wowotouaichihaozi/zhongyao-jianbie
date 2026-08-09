import type { ElegantConstRoute, ElegantRoute } from '@elegant-router/types';
import { generatedRoutes } from '../elegant/routes';
import { layouts, views } from '../elegant/imports';
import { transformElegantRoutesToVueRoutes } from '../elegant/transform';

const adminRoutes = [
  {
    name: 'dashboard',
    path: '/dashboard',
    component: 'layout.base$view.dashboard',
    meta: {
      title: '数据大屏',
      icon: 'mdi:view-dashboard-outline',
      order: 1
    }
  },
  {
    name: 'manage',
    path: '/manage',
    component: 'layout.base',
    redirect: '/manage/user',
    meta: {
      title: '用户管理',
      icon: 'mdi:account-group-outline',
      order: 2
    },
    children: [
      {
        name: 'manage_user',
        path: '/manage/user',
        component: 'view.manage_user',
        meta: {
          title: '用户管理',
          icon: 'mdi:account-details-outline',
          order: 1
        }
      },
      {
        name: 'manage_user-detail',
        path: '/manage/user-detail/:id',
        component: 'view.manage_user-detail',
        meta: {
          title: '用户详情',
          hideInMenu: true,
          activeMenu: 'manage_user'
        }
      }
    ]
  },
  {
    name: 'agents',
    path: '/agents',
    component: 'layout.base$view.agents',
    meta: {
      title: '智能体监控',
      icon: 'mdi:robot-outline',
      order: 3
    }
  },
  {
    name: 'tasks',
    path: '/tasks',
    component: 'layout.base$view.tasks',
    meta: {
      title: '资源任务记录',
      icon: 'mdi:clipboard-text-clock-outline',
      order: 4
    }
  },
  {
    name: 'logs',
    path: '/logs',
    component: 'layout.base$view.logs',
    meta: {
      title: '运行监控',
      icon: 'mdi:server-outline',
      order: 5
    }
  }
] as unknown as ElegantRoute[];

/** create routes when the auth route mode is static */
export function createStaticRoutes() {
  const constantRoutes = generatedRoutes.filter(item => item.meta?.constant) as ElegantRoute[];

  return {
    constantRoutes,
    authRoutes: adminRoutes
  };
}

/**
 * Get auth vue routes
 *
 * @param routes Elegant routes
 */
export function getAuthVueRoutes(routes: ElegantConstRoute[]) {
  return transformElegantRoutesToVueRoutes(routes, layouts, views);
}
