import { type McpServer } from '@/entities/mcp/types';

const mockServers: McpServer[] = [
  {
    id: 'finance-ops',
    name: 'FinanceOps',
    description: 'Финансовый инструментарий: счета, транзакции, отчеты.',
    enabled: true,
    latencyMs: 112,
    tools: [
      {
        id: 'ledger',
        name: 'ledger',
        description: 'Запрос по бухгалтерии',
        command: 'finance-ops.ledger.query',
      },
      {
        id: 'finance',
        name: 'forecast',
        description: 'Прогноз cash-flow',
        command: 'finance-ops.finance.forecast',
      },
      {
        id: 'invoice',
        name: 'invoice',
        description: 'Создать инвойс',
        command: 'finance-ops.invoice.create',
      },
    ],
  },
  {
    id: 'crm',
    name: 'CRM Insight',
    description: 'Работа с клиентами, сделки, уведомления.',
    enabled: true,
    latencyMs: 184,
    tools: [
      {
        id: 'deal',
        name: 'deal',
        description: 'Поиск сделки',
        command: 'crm.deal.lookup',
      },
      {
        id: 'contact',
        name: 'contact',
        description: 'Обновить контакт',
        command: 'crm.contact.update',
      },
      {
        id: 'notify',
        name: 'notify',
        description: 'Отправить уведомление',
        command: 'crm.notify.send',
      },
    ],
  },
  {
    id: 'analytics',
    name: 'AnalyticsLab',
    description: 'Маркетинг и продуктовая аналитика.',
    enabled: false,
    latencyMs: 96,
    tools: [
      {
        id: 'cohort',
        name: 'cohort',
        description: 'Когортный анализ',
        command: 'analytics.analytics.cohort',
      },
      {
        id: 'abtest',
        name: 'abtest',
        description: 'Запустить A/B тест',
        command: 'analytics.ab.run',
      },
      {
        id: 'funnel',
        name: 'funnel',
        description: 'Воронка',
        command: 'analytics.funnel.inspect',
      },
    ],
  },
];

export async function fetchMockServers(): Promise<McpServer[]> {
  await delay(180);
  return mockServers;
}

async function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
