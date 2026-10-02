import Sidebar from "../../components/Sidebar";
import AuthGuard from "../../components/AuthGuard";
export default function WorkspaceLayout({children}:{children:React.ReactNode}){return <AuthGuard><div className="shell"><Sidebar/><main className="main">{children}</main></div></AuthGuard>}
