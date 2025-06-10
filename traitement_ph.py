def main():
    st.set_page_config(page_title="CNA – Tableau de Bord Archives", layout="wide")
    
    # Initialiser la base de données
    db = DatabaseManager()
    
    # Vérifier l'authentification
    if not check_authentication(db):
        # L'utilisateur n'est pas encore authentifié, arrêter l'exécution
        return
    
    # Si l'utilisateur est authentifié, continuer avec l'application normale
    stats_calc = StatisticsCalculator(db)

    st.sidebar.title("CNA – Menu")
    # Ajouter un bouton de déconnexion
    if st.sidebar.button("🚪 Se déconnecter"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.sidebar.markdown("---")
    
    section = st.sidebar.radio(
        "Navigation",
        ("🏠 Accueil", "➕ Nouvelle saisie", "📊 Vue d'ensemble", "📋 Détail", "⚙️ Paramètres", "👥 Archivistes")
    )

    if section == "🏠 Accueil":
        # CSS pour l'entête avec dégradé vert-orange sur fond noir
        st.markdown("""
        <style>
        .header-container {
            background: linear-gradient(135deg, #000000 0%, #2d5016 30%, #ff6b35 70%, #000000 100%);
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .header-title {
            color: white;
            font-size: 2.5rem;
            font-weight: bold;
            text-align: center;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        }
        .header-subtitle {
            color: #f0f0f0;
            font-size: 1.2rem;
            text-align: center;
            margin: 0.5rem 0 0 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.6);
        }
        .welcome-text {
            background: linear-gradient(90deg, #2d5016, #ff6b35);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 1.1rem;
            font-weight: 600;
            text-align: center;
            margin: 1rem 0;
        }
        .menu-section {
            background: rgba(255, 255, 255, 0.95);
            padding: 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .menu-item {
            display: flex;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #eee;
        }
        .menu-item:last-child {
            border-bottom: none;
        }
        .menu-emoji {
            font-size: 1.2rem;
            margin-right: 0.8rem;
        }
        .menu-title {
            font-weight: bold;
            color: #2d5016;
        }
        .menu-desc {
            color: #666;
            margin-left: 0.3rem;
        }
        </style>
        """, unsafe_allow_html=True)

        # Entête principal avec dégradé
        st.markdown("""
        <div class="header-container">
            <h1 class="header-title">🗃️ Centre National des Archives</h1>
            <p class="header-subtitle">Système de Gestion Documentaire</p>
        </div>
        """, unsafe_allow_html=True)

        # Message de bienvenue avec style
        st.markdown("""
        <p class="welcome-text">Bienvenue dans le tableau de gestion du traitement physique.</p>
        """, unsafe_allow_html=True)

        # Menu stylisé
        st.markdown("""
        <div class="menu-section">
            <h3 style="color: #2d5016; text-align: center; margin-bottom: 1rem;">📋 Navigation Principale</h3>
            
            <div class="menu-item">
                <span class="menu-emoji">➕</span>
                <span class="menu-title">Nouvelle saisie</span>
                <span class="menu-desc">: enregistrer un traitement de dossiers physiques.</span>
            </div>
            
            <div class="menu-item">
                <span class="menu-emoji">📊</span>
                <span class="menu-title">Vue d'ensemble</span>
                <span class="menu-desc">: consulter les KPIs et performances globales.</span>
            </div>
            
            <div class="menu-item">
                <span class="menu-emoji">📋</span>
                <span class="menu-title">Détail</span>
                <span class="menu-desc">: historique des traitements et performances par archiviste.</span>
            </div>
            
            <div class="menu-item">
                <span class="menu-emoji">⚙️</span>
                <span class="menu-title">Paramètres</span>
                <span class="menu-desc">: configurer stock initial, objectifs & mots de passe.</span>
            </div>
            
            <div class="menu-item">
                <span class="menu-emoji">👥</span>
                <span class="menu-title">Archivistes</span>
                <span class="menu-desc">: gérer la liste des archivistes du CNA.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Informations complémentaires
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("📁 **Traitement Physique**\n\nSuivi en temps réel du traitement des dossiers d'archives physiques.")
        
        with col2:
            st.success("📈 **Performances**\n\nAnalyse détaillée des performances individuelles et collectives.")
        
        with col3:
            st.warning("🎯 **Objectifs**\n\nSuivi des objectifs journaliers et progression globale.")

        sidebar_authentication(db)

    elif section == "➕ Nouvelle saisie":
        formulaire_saisie(db)

    elif section == "📊 Vue d'ensemble":
        afficher_kpis_et_performances(db, stats_calc)

    elif section == "📋 Détail":
        afficher_tableaux(db, stats_calc)

    elif section == "⚙️ Paramètres":
        pwd = st.text_input("Entrez le mot de passe admin pour accéder aux paramètres :", type="password")
        if pwd == db.obtenir_parametre('mot_de_passe'):
            page_parametres(db)
        elif pwd:
            st.error("❌ Mot de passe incorrect.")

    elif section == "👥 Archivistes":
        page_archivistes(db)
