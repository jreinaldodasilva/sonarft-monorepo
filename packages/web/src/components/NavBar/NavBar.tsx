import React, { useContext } from "react";
import { Link } from "react-router-dom";
import { AuthContext } from "../../hooks/AuthProvider";
import logo from "../../assets/img/sonarftlogo.png";
import "./navbar.css";

const NavBar: React.FC = () => {
    const { user, handleLogin, handleLogout } = useContext(AuthContext);

    return (
        <nav className="nav">
            <section className="sectionLogo">
                <img src={logo} alt="SonarFT" className="logo" />
                <Link className="nav-link" to="/"><span className="nav-title">S<span className="nav-accent">o</span>narFT</span></Link>
            </section>
            <section className="sectionLinks">
                <Link className="nav-link" to="/crypto"><span className="nav-title">Dashboard</span></Link>
            </section>
            <section className="sectionLogin">
                {user
                    ? <button onClick={handleLogout}>Sign Out</button>
                    : <button onClick={handleLogin}>Sign In</button>
                }
            </section>
        </nav>
    );
};

export default NavBar;
