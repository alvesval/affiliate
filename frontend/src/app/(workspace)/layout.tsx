import Sidebar from "../../components/Sidebar";
import AuthGuard from "../../components/AuthGuard";
import WorkspaceHeader from "../../components/WorkspaceHeader";
export default function WorkspaceLayout({children}:{children:React.ReactNode}){return <AuthGuard><div className="shell"><Sidebar/><div className="workspace-area"><WorkspaceHeader/><main className="main">{children}</main></div></div></AuthGuard>}
