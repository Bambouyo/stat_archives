# Remplacer la section if section == "🏠 Accueil": par :

    if section == "🏠 Accueil":
        # CSS simplifié pour l'entête
        st.markdown("""
        <style>
        .header-container {
            background: linear-gradient(135deg, #000000 0%, #2d5016 30%, #ff6b35 70%, #000000 100%);
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            text-align: center;
        }
        .header-title {
            color: white;
            font-size: 2.5rem;
            font-weight: bold;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        }
        .header-subtitle {
            color: #f0f0f0;
            font-size: 1.2rem;
            margin: 0.5rem 0 0 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.6);
        }
        .welcome-text {
            font-size: 1.3rem;
            font-weight: 600;
            text-align: center;
            color: #2d5016;
            margin: 1.5rem 0;
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

        # Message de bienvenue
        st.markdown("""
        <p class="welcome-text">🔥 Bienvenue dans le tableau de gestion du traitement physique 🔥</p>
        """, unsafe_allow_html=True)

        # Navigation avec Streamlit natif - plus fiable
        st.markdown("### 📋 Navigation Principale")
        
        # Créer des colonnes pour un affichage plus structuré
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **➕ Nouvelle saisie**  
            📝 Enregistrer un traitement de dossiers physiques
            
            **📊 Vue d'ensemble**  
            📈 Consulter les KPIs et performances globales
            
            **📋 Détail**  
            📊 Historique des traitements et performances par archiviste
            """)
        
        with col2:
            st.markdown("""
            **⚙️ Paramètres**  
            🔧 Configurer stock initial, objectifs & mots de passe
            
            **👥 Archivistes**  
            👨‍💼 Gérer la liste des archivistes du CNA
            """)

        st.markdown("---")

        # Informations complémentaires avec des cards
        st.markdown("### 🎯 Fonctionnalités principales")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("""
            **📁 Traitement Physique**
            
            • Saisie journalière ou par période
            • Calcul automatique des jours ouvrés
            • Suivi en temps réel des dossiers traités
            """)
        
        with col2:
            st.success("""
            **📈 Performances**
            
            • Analyse hebdomadaire, mensuelle, annuelle
            • Classement des archivistes
            • Tableaux de bord détaillés
            """)
        
        with col3:
            st.warning("""
            **🎯 Objectifs**
            
            • Suivi des objectifs journaliers
            • Progression globale
            • Export des analyses
            """)

        # Métriques rapides en bas de page
        st.markdown("---")
        st.markdown("### 📊 Aperçu rapide")
        
        # Calculer quelques stats de base pour l'affichage
        kpis = stats_calc.calculer_kpis_globaux()
        
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric(
                label="📦 Stock initial", 
                value=f"{kpis['stock_initial']:,}".replace(",", " ")
            )
        
        with metric_col2:
            st.metric(
                label="✅ Dossiers traités", 
                value=f"{kpis['dossiers_traites']:,}".replace(",", " ")
            )
        
        with metric_col3:
            st.metric(
                label="📊 Progression", 
                value=f"{kpis['pourcentage_traite']:.1f}%"
            )
        
        with metric_col4:
            st.metric(
                label="📋 Restant", 
                value=f"{kpis['stock_restant']:,}".replace(",", " ")
            )

        # Sidebar admin
        sidebar_authentication(db)
