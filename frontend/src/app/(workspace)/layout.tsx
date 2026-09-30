import Sidebar from "../../components/Sidebar";
export default function WorkspaceLayout({children}:{children:React.ReactNode}){return <div className="shell"><Sidebar/><main className="main">{children}</main></div>}
