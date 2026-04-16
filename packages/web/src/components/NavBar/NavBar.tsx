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
                <Link className="nav-link" to="/"><h1>S<span>o</span>narFT</h1></Link>
            </section>
            <section className="sectionLinks">
                <Link className="nav-link" to="/crypto"><h1>Crypt<span>o</span></h1></Link>
                <Link className="nav-link" to="/cryptochatgpt"><h1>Crypt<span>o</span>ChatGPT</h1></Link>
                <Link className="nav-link" to="/doggy"><h1>D<span>o</span>ggy</h1></Link>
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
