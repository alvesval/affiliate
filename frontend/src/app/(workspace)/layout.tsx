import AuthGuard from '../../components/AuthGuard';
import WorkspaceShell from '../../components/WorkspaceShell';
export default function WorkspaceLayout({children}:{children:React.ReactNode}){return <AuthGuard><WorkspaceShell>{children}</WorkspaceShell></AuthGuard>}
