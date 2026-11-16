import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <nav className="navbar">
      <div className="navbar-brand">Legal Contract Analyzer</div>
      <div className="navbar-links">
        <Link to="/contracts">Contracts</Link>
        <Link to="/queries">Query History</Link>
      </div>
      <div className="navbar-user">
        <span>
          {user.email} <em>({user.role})</em>
        </span>
        <button onClick={handleLogout}>Log out</button>
      </div>
    </nav>
  );
}
