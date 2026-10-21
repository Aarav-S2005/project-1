import dotenv from 'dotenv';
import { createUsersApp } from './services/users';
import { createDocumentsApp } from './services/documents';
import { createPayrollApp } from './services/payroll';
import { createAdminApp } from './services/admin';

dotenv.config();

const USERS_PORT = parseInt(process.env.USERS_PORT || '4010', 10);
const DOCUMENTS_PORT = parseInt(process.env.DOCUMENTS_PORT || '4011', 10);
const PAYROLL_PORT = parseInt(process.env.PAYROLL_PORT || '4012', 10);
const ADMIN_PORT = parseInt(process.env.ADMIN_PORT || '4013', 10);

function startServices() {
  const usersApp = createUsersApp();
  const docsApp = createDocumentsApp();
  const payrollApp = createPayrollApp();
  const adminApp = createAdminApp();

  const usersServer = usersApp.listen(USERS_PORT, () => {
    console.log(`[Users Service] listening on http://localhost:${USERS_PORT}`);
  });

  const docsServer = docsApp.listen(DOCUMENTS_PORT, () => {
    console.log(`[Documents Service] listening on http://localhost:${DOCUMENTS_PORT}`);
  });

  const payrollServer = payrollApp.listen(PAYROLL_PORT, () => {
    console.log(`[Payroll Service] listening on http://localhost:${PAYROLL_PORT}`);
  });

  const adminServer = adminApp.listen(ADMIN_PORT, () => {
    console.log(`[Admin Service] listening on http://localhost:${ADMIN_PORT}`);
  });

  return { usersServer, docsServer, payrollServer, adminServer };
}

if (process.env.NODE_ENV !== 'test') {
  startServices();
}

export { startServices };
