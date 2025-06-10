#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TABLEAU DE BORD GESTION DES ARCHIVES - VERSION STREAMLIT AMÉLIORÉE
- Authentification globale requise pour accéder à l'application
- Ajout/Suppression d'archivistes
- Sélection d'intervalle de date (deux date_inputs)
- Calcul du nombre de jours travaillés par archiviste (5 j/semaine)
- Consultation du nombre total de dossiers entre deux dates dans la saisie
- Possibilité de saisir journalièrement ou par période (hebdo, mensuel, annuel)
- Export d'une analyse formatée comme le CSV fourni
- Suppression de saisies par date ou par archiviste
- Performances annuelles par archiviste avec jours ouvrés
- Interface redesignée avec dégradé vert-orange et thème archives
- Modification et suppression de saisies individuelles
- Objectif 200 dossiers/jour, atteint à 90% (180 dossiers)
- Modification des saisies depuis le cumul annuel
"""

import streamlit as st
import sqlite3
import csv
from datetime import datetime, timedelta, date
from io import StringIO
import pandas as pd

# ============================================================================
# CONFIGURATION ET CONSTANTES
# ============================================================================

class Config:
    DB_PATH = "archives_simple.sqlite"
    STOCK_INITIAL = 150000
    OBJECTIF_JOURNALIER = 200
    SEUIL_OBJECTIF = 0.9  # 90% pour atteindre l'objectif (180 dossiers)
    MOT_DE_PASSE_ADMIN = "archives2025"
    MOT_DE_PASSE_APP = "CNA2025"
    ARCHIVISTES_DEFAULT = [
        "ABDOU DIATTA", "ALPHONSE K DIOUF", "AMINATA NDIAYE",
        "BERNARD B OGUIKI", "FATIM MBAYE", "JOSEPH M N DIOUF",
        "KANI TOURE", "SANOU WAGUE", "SERIGNE B CISS"
    ]

# ============================================================================
# GESTIONNAIRE DE BASE DE DONNÉES
# ============================================================================

class DatabaseManager:
    def __init__(self, db_path=Config.DB_PATH):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS traitements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_traitement DATE NOT NULL,
                    archiviste TEXT NOT NULL,
                    dossiers_traites INTEGER NOT NULL,
                    commentaire TEXT,
                    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parametres (
                    cle TEXT PRIMARY KEY,
                    valeur TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS archivistes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT UNIQUE NOT NULL,
                    actif BOOLEAN DEFAULT 1
                )
            ''')
            conn.commit()
            self.init_default_params()

    def init_default_params(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            params = [
                ('stock_initial', str(Config.STOCK_INITIAL)),
                ('objectif_journalier', str(Config.OBJECTIF_JOURNALIER)),
                ('seuil_objectif', str(Config.SEUIL_OBJECTIF)),
                ('mot_de_passe', Config.MOT_DE_PASSE_ADMIN),
                ('mot_de_passe_app', Config.MOT_DE_PASSE_APP)
            ]
            for cle, valeur in params:
                cursor.execute(
                    "INSERT OR IGNORE INTO parametres (cle, valeur) VALUES (?, ?)",
                    (cle, valeur)
                )
            conn.commit()
            cursor.execute("SELECT COUNT(*) FROM archivistes")
            count = cursor.fetchone()[0]
            if count == 0:
                self.reinitialiser_archivistes_complet(cursor)
                conn.commit()

    def reinitialiser_archivistes_complet(self, cursor):
        archivistes_cna = Config.ARCHIVISTES_DEFAULT
        placeholders = ','.join(['?'] * len(archivistes_cna))
        cursor.execute(f"""
            UPDATE traitements
            SET archiviste = 'ARCHIVISTE INCONNU'
            WHERE archiviste NOT IN ({placeholders})
        """, archivistes_cna)
        nb_updates = cursor.rowcount

        cursor.execute("DELETE FROM archivistes")
        for archiviste in archivistes_cna:
            cursor.execute(
                "INSERT INTO archivistes (nom, actif) VALUES (?, 1)",
                (archiviste,)
            )
        if nb_updates > 0:
            cursor.execute(
                "INSERT INTO archivistes (nom, actif) VALUES (?, 0)",
                ("ARCHIVISTE INCONNU",)
            )

    def obtenir_archivistes(self, actifs_seulement=True):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if actifs_seulement:
                cursor.execute(
                    "SELECT nom FROM archivistes WHERE actif = 1 ORDER BY nom"
                )
                return [row[0] for row in cursor.fetchall()]
            else:
                cursor.execute(
                    "SELECT nom, actif FROM archivistes ORDER BY actif DESC, nom"
                )
                return cursor.fetchall()

    def ajouter_archiviste(self, nom):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO archivistes (nom, actif) VALUES (?, 1)",
                (nom,)
            )
            conn.commit()

    def desactiver_archiviste(self, nom):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE archivistes SET actif = 0 WHERE nom = ?",
                (nom,)
            )
            conn.commit()

    def supprimer_archiviste(self, nom):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM archivistes WHERE nom = ?",
                (nom,)
            )
            conn.commit()

    def obtenir_parametre(self, cle):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT valeur FROM parametres WHERE cle = ?",
                (cle,)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def mettre_a_jour_parametre(self, cle, valeur):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO parametres (cle, valeur) VALUES (?, ?)",
                (cle, valeur)
            )
            conn.commit()

    def ajouter_traitement(self, date_traitement, archiviste, dossiers_traites, commentaire=""):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO traitements (date_traitement, archiviste, dossiers_traites, commentaire)
                VALUES (?, ?, ?, ?)
            ''', (date_traitement, archiviste, dossiers_traites, commentaire))
            conn.commit()
            return cursor.lastrowid

    def obtenir_traitements(self, date_debut=None, date_fin=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM traitements WHERE 1=1"
            params = []
            if date_debut:
                query += " AND date_traitement >= ?"
                params.append(date_debut)
            if date_fin:
                query += " AND date_traitement <= ?"
                params.append(date_fin)
            query += " ORDER BY date_traitement DESC"
            cursor.execute(query, params)
            cols = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(cols, row)) for row in rows]

    def obtenir_traitements_par_archiviste(self, archiviste, date_debut=None, date_fin=None):
        """Obtenir les traitements d'un archiviste spécifique"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM traitements WHERE archiviste = ?"
            params = [archiviste]
            if date_debut:
                query += " AND date_traitement >= ?"
                params.append(date_debut)
            if date_fin:
                query += " AND date_traitement <= ?"
                params.append(date_fin)
            query += " ORDER BY date_traitement DESC"
            cursor.execute(query, params)
            cols = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(cols, row)) for row in rows]

    def reinitialiser_donnees(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM traitements")
            conn.commit()

# ============================================================================
# CALCULATEUR DE STATISTIQUES
# ============================================================================

class StatisticsCalculator:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def _jours_ouvres(self, dates_list):
        jours = set()
        for d_str in dates_list:
            try:
                d = datetime.strptime(d_str, "%Y-%m-%d").date()
                if d.weekday() < 5:
                    jours.add(d)
            except:
                continue
        return len(jours)

    def _calculer_jours_ouvres_annee(self, annee):
        """Calcule le nombre total de jours ouvrés dans une année"""
        debut = date(annee, 1, 1)
        fin = date(annee, 12, 31)
        
        current = debut
        jours_ouvres = 0
        while current <= fin:
            if current.weekday() < 5:  # Lundi=0 à Vendredi=4
                jours_ouvres += 1
            current += timedelta(days=1)
        
        return jours_ouvres

    def calculer_kpis_globaux(self):
        traitements = self.db.obtenir_traitements()
        stock_initial = int(self.db.obtenir_parametre('stock_initial') or 0)
        if not traitements:
            return {
                'stock_initial': stock_initial,
                'dossiers_traites': 0,
                'stock_restant': stock_initial,
                'pourcentage_traite': 0.0
            }
        total = sum(t['dossiers_traites'] for t in traitements)
        restant = max(0, stock_initial - total)
        pct = (total / stock_initial) * 100 if stock_initial > 0 else 0
        return {
            'stock_initial': stock_initial,
            'dossiers_traites': total,
            'stock_restant': restant,
            'pourcentage_traite': round(pct, 2)
        }

    def calculer_performances_journalieres(self, date_ref=None):
        """Calcul avec logique des 90%"""
        if date_ref is None:
            date_ref = date.today()
        date_str = date_ref.strftime('%Y-%m-%d')
        traitements = self.db.obtenir_traitements(date_str, date_str)
        objectif = int(self.db.obtenir_parametre('objectif_journalier') or 200)
        seuil_objectif = float(self.db.obtenir_parametre('seuil_objectif') or 0.9)
        seuil_reussite = objectif * seuil_objectif  # 90% de l'objectif = réussite
        
        if not traitements:
            return {
                'date': date_ref,
                'dossiers_traites': 0,
                'objectif': objectif,
                'seuil_reussite': int(seuil_reussite),
                'taux_realisation': 0.0,
                'objectif_atteint': False,
                'ecart': -int(seuil_reussite)
            }
        
        total = sum(t['dossiers_traites'] for t in traitements)
        
        # Calcul : on considère 100% à partir de 90% de l'objectif
        if total >= seuil_reussite:
            taux = (total / objectif) * 100  # Peut dépasser 100%
            objectif_atteint = True
        else:
            taux = (total / seuil_reussite) * 90  # Échelle jusqu'à 90%
            objectif_atteint = False
        
        ecart = total - seuil_reussite
        
        return {
            'date': date_ref,
            'dossiers_traites': total,
            'objectif': objectif,
            'seuil_reussite': int(seuil_reussite),
            'taux_realisation': round(taux, 2),
            'objectif_atteint': objectif_atteint,
            'ecart': int(ecart)
        }

    def calculer_performances_hebdomadaires(self, date_ref=None):
        """Calcul avec logique des 90%"""
        if date_ref is None:
            date_ref = date.today()
        debut_semaine = date_ref - timedelta(days=date_ref.weekday())
        fin_semaine = debut_semaine + timedelta(days=6)
        traitements = self.db.obtenir_traitements(
            debut_semaine.strftime('%Y-%m-%d'),
            fin_semaine.strftime('%Y-%m-%d')
        )
        objectif_journalier = int(self.db.obtenir_parametre('objectif_journalier') or 200)
        seuil_objectif = float(self.db.obtenir_parametre('seuil_objectif') or 0.9)
        objectif_hebdo = objectif_journalier * 5  # 5 jours ouvrés
        seuil_hebdo = objectif_hebdo * seuil_objectif  # 90% de l'objectif hebdo
        
        if not traitements:
            return {
                'semaine': f"{debut_semaine.strftime('%d/%m')} - {fin_semaine.strftime('%d/%m/%Y')}",
                'dossiers_traites': 0,
                'objectif': objectif_hebdo,
                'seuil_reussite': int(seuil_hebdo),
                'taux_realisation': 0.0,
                'objectif_atteint': False
            }
        
        total = sum(t['dossiers_traites'] for t in traitements)
        
        # Même logique que journalier
        if total >= seuil_hebdo:
            taux = (total / objectif_hebdo) * 100  # Peut dépasser 100%
            objectif_atteint = True
        else:
            taux = (total / seuil_hebdo) * 90
            objectif_atteint = False
        
        return {
            'semaine': f"{debut_semaine.strftime('%d/%m')} - {fin_semaine.strftime('%d/%m/%Y')}",
            'dossiers_traites': total,
            'objectif': objectif_hebdo,
            'seuil_reussite': int(seuil_hebdo),
            'taux_realisation': round(taux, 2),
            'objectif_atteint': objectif_atteint
        }

    def obtenir_performances_hebdo_par_archiviste(self, date_ref=None):
        """Calcul avec logique des 90%"""
        if date_ref is None:
            date_ref = date.today()
        debut_semaine = date_ref - timedelta(days=date_ref.weekday())
        fin_semaine = debut_semaine + timedelta(days=6)
        traitements = self.db.obtenir_traitements(
            debut_semaine.strftime('%Y-%m-%d'),
            fin_semaine.strftime('%Y-%m-%d')
        )
        if not traitements:
            return []
            
        stats = {}
        for t in traitements:
            arch = t['archiviste']
            stats.setdefault(arch, []).append(t['date_traitement'])
        
        result = []
        objectif_journalier = int(self.db.obtenir_parametre('objectif_journalier') or 200)
        seuil_objectif = float(self.db.obtenir_parametre('seuil_objectif') or 0.9)
        objectif_hebdo = objectif_journalier * 5
        seuil_hebdo = objectif_hebdo * seuil_objectif
        
        for arch, dates in stats.items():
            total = sum(
                t['dossiers_traites'] for t in traitements if t['archiviste'] == arch
            )
            jours_ouvres = self._jours_ouvres(dates)
            
            # Calculer le taux selon la nouvelle logique
            if total >= seuil_hebdo:
                taux = (total / objectif_hebdo) * 100  # Peut dépasser 100%
                statut = "🟢 Objectif atteint"
            else:
                taux = (total / seuil_hebdo) * 90
                if taux >= 80:
                    statut = "🟡 Proche objectif"
                else:
                    statut = "🔴 En retard"
            
            moy = (total / jours_ouvres) if jours_ouvres > 0 else 0
            
            result.append({
                'archiviste': arch,
                'total_dossiers': total,
                'jours_travailles': jours_ouvres,
                'moyenne_jour': round(moy, 1),
                'taux_hebdo': round(taux, 1),
                'objectif_hebdo': objectif_hebdo,
                'seuil_reussite': int(seuil_hebdo),
                'statut': statut
            })
        
        result.sort(key=lambda x: x['taux_hebdo'], reverse=True)
        return result

    def obtenir_performances_30j_par_archiviste(self):
        """Calcul avec logique des 90%"""
        date_fin = date.today()
        date_debut = date_fin - timedelta(days=30)
        traitements = self.db.obtenir_traitements(
            date_debut.strftime('%Y-%m-%d'),
            date_fin.strftime('%Y-%m-%d')
        )
        if not traitements:
            return []
            
        stats = {}
        for t in traitements:
            arch = t['archiviste']
            stats.setdefault(arch, []).append(t['date_traitement'])
        
        result = []
        objectif = int(self.db.obtenir_parametre('objectif_journalier') or 200)
        seuil_objectif = float(self.db.obtenir_parametre('seuil_objectif') or 0.9)
        seuil_journalier = objectif * seuil_objectif  # 180 dossiers pour atteindre l'objectif
        
        for arch, dates in stats.items():
            total = sum(
                t['dossiers_traites'] for t in traitements if t['archiviste'] == arch
            )
            jours_ouvres = self._jours_ouvres(dates)
            moy = (total / jours_ouvres) if jours_ouvres > 0 else 0
            
            # Calculer selon la nouvelle logique
            if moy >= seuil_journalier:
                taux_obj = (moy / objectif) * 100  # Peut dépasser 100%
                statut = "🟢 Objectif atteint"
            else:
                taux_obj = (moy / seuil_journalier) * 90
                if taux_obj >= 80:
                    statut = "🟡 Proche objectif"
                else:
                    statut = "🔴 En retard"
            
            result.append({
                'archiviste': arch,
                'total_dossiers': total,
                'jours_travailles': jours_ouvres,
                'moyenne_jour': round(moy, 1),
                'taux_objectif': round(taux_obj, 1),
                'seuil_journalier': int(seuil_journalier),
                'statut': statut
            })
        
        return result

    def obtenir_performances_annuelles_par_archiviste(self, annee=None):
        """Calcul avec logique des 90%"""
        if annee is None:
            annee = date.today().year
        
        date_debut = date(annee, 1, 1)
        date_fin = date(annee, 12, 31)
        
        traitements = self.db.obtenir_traitements(
            date_debut.strftime('%Y-%m-%d'),
            date_fin.strftime('%Y-%m-%d')
        )
        
        if not traitements:
            return []
        
        stats = {}
        for t in traitements:
            arch = t['archiviste']
            stats.setdefault(arch, []).append(t['date_traitement'])
        
        result = []
        objectif_journalier = int(self.db.obtenir_parametre('objectif_journalier') or 200)
        seuil_objectif = float(self.db.obtenir_parametre('seuil_objectif') or 0.9)
        seuil_journalier = objectif_journalier * seuil_objectif  # 180 dossiers
        
        for arch, dates in stats.items():
            total = sum(
                t['dossiers_traites'] for t in traitements if t['archiviste'] == arch
            )
            
            jours_ouvres = self._jours_ouvres(dates)
            moyenne_jour = (total / jours_ouvres) if jours_ouvres > 0 else 0
            
            # Calculer selon la nouvelle logique
            if moyenne_jour >= seuil_journalier:
                taux_objectif = (moyenne_jour / objectif_journalier) * 100  # Peut dépasser 100%
                statut = "🟢 Excellent"
            else:
                taux_objectif = (moyenne_jour / seuil_journalier) * 90
                if taux_objectif >= 80:
                    statut = "🟡 Correct"
                elif taux_objectif >= 60:
                    statut = "🟠 Moyen"
                else:
                    statut = "🔴 Insuffisant"
            
            jours_ouvres_annee = self._calculer_jours_ouvres_annee(annee)
            couverture_annee = (jours_ouvres / jours_ouvres_annee) * 100 if jours_ouvres_annee > 0 else 0
            
            result.append({
                'archiviste': arch,
                'total_dossiers': total,
                'jours_travailles': jours_ouvres,
                'moyenne_jour': round(moyenne_jour, 1),
                'taux_objectif': round(taux_objectif, 1),
                'couverture_annee': round(couverture_annee, 1),
                'seuil_journalier': int(seuil_journalier),
                'statut': statut,
                'annee': annee
            })
        
        result.sort(key=lambda x: x['taux_objectif'], reverse=True)
        return result

# ============================================================================
# FONCTION D'AUTHENTIFICATION GLOBALE
# ============================================================================

def check_authentication(db: DatabaseManager):
    """Vérifie si l'utilisateur est authentifié pour accéder à l'application"""
    
    # Initialiser l'état de session si nécessaire
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Si déjà authentifié, retourner True
    if st.session_state.authenticated:
        return True
    
    # Sinon, afficher le formulaire de connexion
    st.markdown("""
    <style>
    .main {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Titre centré
    st.markdown("<h1 style='text-align: center;'>🗃️ Centre National des Archives</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Gestion du Traitement Physique</h3>", unsafe_allow_html=True)
    
    # Créer un conteneur centré pour le formulaire
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        st.markdown("### 🔐 Authentification requise")
        
        # Récupérer le mot de passe de l'application depuis la base de données
        mot_de_passe_app = db.obtenir_parametre('mot_de_passe_app')
        
        # Formulaire de connexion
        with st.form("login_form"):
            password = st.text_input("Mot de passe", type="password", placeholder="Entrez le mot de passe")
            submit = st.form_submit_button("Se connecter", use_container_width=True)
            
            if submit:
                if password == mot_de_passe_app:
                    st.session_state.authenticated = True
                    st.success("✅ Connexion réussie!")
                    st.rerun()
                else:
                    st.error("❌ Mot de passe incorrect")
        
        st.markdown("---")
        st.info("💡 Pour obtenir le mot de passe, contactez l'administrateur du système.")
    
    return False

# ============================================================================
# FONCTIONS STREAMLIT
# ============================================================================

def sidebar_authentication(db: DatabaseManager):
    st.sidebar.header("🔒 Administration")
    pwd = st.sidebar.text_input("Mot de passe admin", type="password")
    valid_pwd = db.obtenir_parametre('mot_de_passe')
    if pwd and pwd == valid_pwd:
        st.sidebar.success("✅ Authentifié")
        if st.sidebar.button("🗑️ Réinitialiser toutes les données"):
            if st.sidebar.checkbox("⚠️ Confirmer la réinitialisation"):
                db.reinitialiser_donnees()
                st.sidebar.info("✅ Toutes les données de traitements ont été supprimées.")
    elif pwd:
        st.sidebar.error("⚠️ Mot de passe incorrect")

def formulaire_saisie(db: DatabaseManager):
    st.header("➕ Nouvelle saisie de traitement")

    # Section : total dossiers entre deux dates
    st.subheader("📅 Consulter total de dossiers entre deux dates")
    colA, colB = st.columns(2)
    with colA:
        interval_start = st.date_input(
            "Date début (consultation)",
            value=date.today() - timedelta(days=7),
            key="interval_start"
        )
    with colB:
        interval_end = st.date_input(
            "Date fin (consultation)",
            value=date.today(),
            key="interval_end"
        )
    if interval_start > interval_end:
        st.warning("La date début doit être antérieure ou égale à la date fin.")
    else:
        traitements_interval = db.obtenir_traitements(
            interval_start.strftime('%Y-%m-%d'),
            interval_end.strftime('%Y-%m-%d')
        )
        total_interval = sum(
            t['dossiers_traites'] for t in traitements_interval
        ) if traitements_interval else 0
        st.info(
            f"📊 Total dossiers du {interval_start.strftime('%d/%m/%Y')} "
            f"au {interval_end.strftime('%d/%m/%Y')} : {total_interval}"
        )

    st.markdown("---")

    # Créer des onglets pour organiser les fonctionnalités
    tab1, tab2, tab3 = st.tabs([
        "➕ Nouvelle saisie", 
        "✏️ Modifier une saisie", 
        "🗑️ Supprimer une saisie"
    ])

    # ONGLET 1 : NOUVELLE SAISIE
    with tab1:
        st.subheader("🔄 Choix du mode de saisie")
        mode = st.radio("Saisir par :", ("Journalier", "Par période"), index=0, key="mode_saisie")

        if mode == "Journalier":
            with st.form("form_journalier", clear_on_submit=True):
                date_input = st.date_input("Date de traitement", value=date.today())
                archivistes = db.obtenir_archivistes()
                archiviste_sel = st.selectbox("Archiviste", options=archivistes)
                dossiers = st.number_input("Dossiers traités", min_value=0, step=1, value=0)
                commentaire = st.text_area("Commentaire (optionnel)", height=80)
                submitted = st.form_submit_button("✅ Valider Journalier")
                if submitted:
                    avertissements = []
                    if date_input.weekday() >= 5:
                        avertissements.append("⚠️ Date en weekend (Samedi ou Dimanche)")
                    if date_input > date.today():
                        avertissements.append("⚠️ La date est dans le futur")
                    if dossiers == 0:
                        avertissements.append("⚠️ Aucun dossier traité")
                    if dossiers > 1000:
                        avertissements.append("⚠️ Nombre très élevé de dossiers")
                    if avertissements:
                        st.warning("Votre saisie comporte des points d'attention :")
                        for msg in avertissements:
                            st.markdown(f"- {msg}")
                        ok = st.checkbox("Je confirme malgré les avertissements", key="ok_journalier")
                        if not ok:
                            st.info("Cochez la case pour confirmer malgré les avertissements.")
                            return
                    try:
                        db.ajouter_traitement(
                            date_input.strftime("%Y-%m-%d"),
                            archiviste_sel,
                            int(dossiers),
                            commentaire
                        )
                        st.success(
                            f"✅ Traitement enregistré : {dossiers} dossiers par {archiviste_sel} "
                            f"le {date_input.strftime('%d/%m/%Y')}"
                        )
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'enregistrement : {e}")

        else:  # Mode Par période
            with st.form("form_periode", clear_on_submit=True):
                st.markdown("**Période de saisie (jours ouvrés uniquement)**")
                perA, perB, perC = st.columns(3)
                with perA:
                    start_per = st.date_input(
                        "Date début",
                        value=date.today() - timedelta(days=7),
                        key="start_per"
                    )
                with perB:
                    end_per = st.date_input(
                        "Date fin",
                        value=date.today(),
                        key="end_per"
                    )
                with perC:
                    archivistes = db.obtenir_archivistes()
                    archiviste_sel2 = st.selectbox("Archiviste", options=archivistes, key="arch_periode")
                total_dossiers_per = st.number_input(
                    "Total dossiers traités sur la période",
                    min_value=0, step=1, value=0, key="total_per"
                )
                commentaire_per = st.text_area("Commentaire (optionnel)", height=80, key="comm_per")
                submitted_per = st.form_submit_button("✅ Valider Période")
                if submitted_per:
                    if start_per > end_per:
                        st.error("La date début doit être antérieure ou égale à la date fin.")
                        return
                    # Construire liste des jours ouvrés
                    current = start_per
                    jours_ouvres = []
                    while current <= end_per:
                        if current.weekday() < 5:
                            jours_ouvres.append(current)
                        current += timedelta(days=1)
                    nb_jours = len(jours_ouvres)
                    if nb_jours == 0:
                        st.error("Aucun jour ouvré dans cette période.")
                        return
                    # Répartir dossiers également
                    base = total_dossiers_per // nb_jours
                    reste = total_dossiers_per % nb_jours
                    try:
                        for i, d in enumerate(jours_ouvres):
                            dossiers_j = base + (1 if i < reste else 0)
                            db.ajouter_traitement(
                                d.strftime("%Y-%m-%d"),
                                archiviste_sel2,
                                dossiers_j,
                                commentaire_per
                            )
                        st.success(
                            f"✅ Période enregistrée : {total_dossiers_per} dossiers répartis "
                            f"sur {nb_jours} jours ouvrés."
                        )
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'enregistrement des entrées : {e}")

    # ONGLET 2 : MODIFIER UNE SAISIE
    with tab2:
        st.subheader("✏️ Modifier une saisie existante")
        
        # Filtres pour rechercher la saisie à modifier
        col_search1, col_search2 = st.columns(2)
        with col_search1:
            date_recherche = st.date_input(
                "Date de la saisie à modifier",
                value=date.today(),
                key="date_recherche_modif"
            )
        with col_search2:
            archivistes_all = ["Tous"] + db.obtenir_archivistes(actifs_seulement=False)
            archiviste_filtre = st.selectbox(
                "Filtrer par archiviste",
                options=archivistes_all,
                key="archiviste_filtre_modif"
            )
        
        # Rechercher les saisies
        date_str = date_recherche.strftime('%Y-%m-%d')
        traitements_jour = db.obtenir_traitements(date_str, date_str)
        
        if archiviste_filtre != "Tous":
            traitements_jour = [t for t in traitements_jour if t['archiviste'] == archiviste_filtre]
        
        if traitements_jour:
            st.write(f"**Saisies trouvées pour le {date_recherche.strftime('%d/%m/%Y')} :**")
            
            # Afficher les saisies sous forme de sélection
            saisies_options = []
            for t in traitements_jour:
                option = f"ID:{t['id']} - {t['archiviste']} - {t['dossiers_traites']} dossiers"
                if t['commentaire']:
                    option += f" - ({t['commentaire'][:50]}...)" if len(t['commentaire']) > 50 else f" - ({t['commentaire']})"
                saisies_options.append((option, t))
            
            if saisies_options:
                saisie_selectionnee = st.selectbox(
                    "Choisir la saisie à modifier :",
                    options=[opt[0] for opt in saisies_options],
                    key="saisie_a_modifier"
                )
                
                # Trouver la saisie correspondante
                traitement_a_modifier = None
                for opt in saisies_options:
                    if opt[0] == saisie_selectionnee:
                        traitement_a_modifier = opt[1]
                        break
                
                if traitement_a_modifier:
                    st.markdown("---")
                    st.write("**Modifier les informations :**")
                    
                    with st.form("form_modification"):
                        # Pré-remplir avec les valeurs actuelles
                        nouvelle_date = st.date_input(
                            "Nouvelle date :",
                            value=datetime.strptime(traitement_a_modifier['date_traitement'], "%Y-%m-%d").date(),
                            key="nouvelle_date_modif"
                        )
                        
                        archivistes_modif = db.obtenir_archivistes()
                        index_archiviste = 0
                        if traitement_a_modifier['archiviste'] in archivistes_modif:
                            index_archiviste = archivistes_modif.index(traitement_a_modifier['archiviste'])
                        
                        nouvel_archiviste = st.selectbox(
                            "Nouvel archiviste :",
                            options=archivistes_modif,
                            index=index_archiviste,
                            key="nouvel_archiviste_modif"
                        )
                        
                        nouveaux_dossiers = st.number_input(
                            "Nouveau nombre de dossiers :",
                            min_value=0,
                            value=traitement_a_modifier['dossiers_traites'],
                            step=1,
                            key="nouveaux_dossiers_modif"
                        )
                        
                        nouveau_commentaire = st.text_area(
                            "Nouveau commentaire :",
                            value=traitement_a_modifier['commentaire'] or "",
                            height=80,
                            key="nouveau_commentaire_modif"
                        )
                        
                        submitted_modif = st.form_submit_button("✅ Enregistrer les modifications")
                        
                        if submitted_modif:
                            try:
                                with sqlite3.connect(db.db_path) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        UPDATE traitements 
                                        SET date_traitement = ?, archiviste = ?, dossiers_traites = ?, commentaire = ?
                                        WHERE id = ?
                                    """, (
                                        nouvelle_date.strftime("%Y-%m-%d"),
                                        nouvel_archiviste,
                                        nouveaux_dossiers,
                                        nouveau_commentaire,
                                        traitement_a_modifier['id']
                                    ))
                                    conn.commit()
                                
                                st.success(f"✅ Saisie ID:{traitement_a_modifier['id']} modifiée avec succès !")
                                st.rerun()  # Actualiser la page
                                
                            except Exception as e:
                                st.error(f"❌ Erreur lors de la modification : {e}")
        else:
            st.info("Aucune saisie trouvée pour cette date et ces critères.")

    # ONGLET 3 : SUPPRIMER UNE SAISIE
    with tab3:
        st.subheader("🗑️ Supprimer une saisie spécifique")
        
        # Filtres pour rechercher la saisie à supprimer
        col_search3, col_search4 = st.columns(2)
        with col_search3:
            date_recherche_suppr = st.date_input(
                "Date de la saisie à supprimer",
                value=date.today(),
                key="date_recherche_suppr"
            )
        with col_search4:
            archivistes_all_suppr = ["Tous"] + db.obtenir_archivistes(actifs_seulement=False)
            archiviste_filtre_suppr = st.selectbox(
                "Filtrer par archiviste",
                options=archivistes_all_suppr,
                key="archiviste_filtre_suppr"
            )
        
        # Rechercher les saisies
        date_str_suppr = date_recherche_suppr.strftime('%Y-%m-%d')
        traitements_jour_suppr = db.obtenir_traitements(date_str_suppr, date_str_suppr)
        
        if archiviste_filtre_suppr != "Tous":
            traitements_jour_suppr = [t for t in traitements_jour_suppr if t['archiviste'] == archiviste_filtre_suppr]
        
        if traitements_jour_suppr:
            st.write(f"**Saisies trouvées pour le {date_recherche_suppr.strftime('%d/%m/%Y')} :**")
            
            # Afficher les saisies sous forme de tableau
            affichage_suppr = []
            for t in traitements_jour_suppr:
                affichage_suppr.append({
                    "ID": t['id'],
                    "Archiviste": t['archiviste'],
                    "Dossiers": t['dossiers_traites'],
                    "Commentaire": t['commentaire'] or ""
                })
            
            df_suppr = pd.DataFrame(affichage_suppr)
            st.dataframe(df_suppr, use_container_width=True)
            
            # Sélection de la saisie à supprimer
            ids_disponibles = [t['id'] for t in traitements_jour_suppr]
            id_a_supprimer = st.selectbox(
                "Choisir l'ID de la saisie à supprimer :",
                options=ids_disponibles,
                key="id_a_supprimer"
            )
            
            # Trouver les détails de la saisie sélectionnée
            saisie_a_supprimer = next((t for t in traitements_jour_suppr if t['id'] == id_a_supprimer), None)
            
            if saisie_a_supprimer:
                st.warning(f"""
                **Attention !** Vous êtes sur le point de supprimer :
                - **ID :** {saisie_a_supprimer['id']}
                - **Date :** {datetime.strptime(saisie_a_supprimer['date_traitement'], "%Y-%m-%d").strftime('%d/%m/%Y')}
                - **Archiviste :** {saisie_a_supprimer['archiviste']}
                - **Dossiers :** {saisie_a_supprimer['dossiers_traites']}
                - **Commentaire :** {saisie_a_supprimer['commentaire'] or 'Aucun'}
                """)
                
                confirmation = st.checkbox(
                    f"⚠️ Je confirme vouloir supprimer définitivement la saisie ID:{id_a_supprimer}",
                    key="confirmation_suppression"
                )
                
                if confirmation:
                    if st.button("🗑️ Supprimer définitivement", type="secondary"):
                        try:
                            with sqlite3.connect(db.db_path) as conn:
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM traitements WHERE id = ?", (id_a_supprimer,))
                                conn.commit()
                            
                            st.success(f"✅ Saisie ID:{id_a_supprimer} supprimée avec succès !")
                            st.rerun()  # Actualiser la page
                            
                        except Exception as e:
                            st.error(f"❌ Erreur lors de la suppression : {e}")
        else:
            st.info("Aucune saisie trouvée pour cette date et ces critères.")
        
        # Section de suppression groupée (comme avant)
        st.markdown("---")
        st.subheader("🗑️ Suppression groupée")
        
        col_group1, col_group2 = st.columns(2)
        
        with col_group1:
            st.markdown("**Supprimer toutes les saisies d'une date :**")
            date_suppr_groupe = st.date_input(
                "Date à supprimer complètement :",
                value=date.today(),
                key="date_suppr_groupe"
            )
            if st.button("🗑️ Supprimer toute la date", key="btn_suppr_date"):
                date_str_groupe = date_suppr_groupe.strftime("%Y-%m-%d")
                with sqlite3.connect(db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM traitements WHERE date_traitement = ?", (date_str_groupe,))
                    n = cursor.rowcount
                    conn.commit()
                if n > 0:
                    st.success(f"✅ {n} saisie(s) supprimée(s) pour le {date_suppr_groupe.strftime('%d/%m/%Y')}.")
                else:
                    st.info(f"Aucune saisie trouvée pour le {date_suppr_groupe.strftime('%d/%m/%Y')}.")
        
        with col_group2:
            st.markdown("**Supprimer toutes les saisies d'un archiviste :**")
            archivistes_suppr_groupe = db.obtenir_archivistes(actifs_seulement=False)
            noms_suppr = [a[0] for a in archivistes_suppr_groupe]
            archiviste_suppr_groupe = st.selectbox(
                "Archiviste à supprimer :",
                options=noms_suppr,
                key="archiviste_suppr_groupe"
            )
            if st.button("🗑️ Supprimer tout l'archiviste", key="btn_suppr_archiviste"):
                with sqlite3.connect(db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM traitements WHERE archiviste = ?", (archiviste_suppr_groupe,))
                    n2 = cursor.rowcount
                    conn.commit()
                if n2 > 0:
                    st.success(f"✅ {n2} saisie(s) supprimée(s) pour l'archiviste « {archiviste_suppr_groupe} ».")
                else:
                    st.info(f"Aucune saisie trouvée pour l'archiviste « {archiviste_suppr_groupe} ».")

def afficher_kpis_et_performances(db: DatabaseManager, stats_calc: StatisticsCalculator):
    """Affichage avec les nouveaux calculs"""
    st.header("📊 Vue d'ensemble")
    kpis = stats_calc.calculer_kpis_globaux()
    perf_jour = stats_calc.calculer_performances_journalieres()
    perf_semaine = stats_calc.calculer_performances_hebdomadaires()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="Stock initial", value=f"{kpis['stock_initial']:,}".replace(",", " "))
    c2.metric(label="Dossiers traités", value=f"{kpis['dossiers_traites']:,}".replace(",", " "))
    c3.metric(label="Stock restant", value=f"{kpis['stock_restant']:,}".replace(",", " "))
    c4.metric(label="% traité", value=f"{kpis['pourcentage_traite']:.1f}%")
    
    st.markdown("---")
    st.subheader("⚡ Performances Journalières")
    
    # Affichage avec seuil
    colj1, colj2, colj3, colj4 = st.columns(4)
    colj1.metric(label="Aujourd'hui", value=perf_jour['dossiers_traites'])
    colj2.metric(label="% réalisé", value=f"{perf_jour['taux_realisation']:.1f}%")
    colj3.metric(label="Seuil (90%)", value=f"{perf_jour['seuil_reussite']}")
    
    # Affichage du statut avec icône
    if perf_jour['objectif_atteint']:
        colj4.success("🎯 Objectif atteint !")
    else:
        colj4.error(f"📉 Écart: {perf_jour['ecart']}")
    
    st.subheader("⚡ Performances Hebdomadaires")
    colh1, colh2, colh3, colh4 = st.columns(4)
    colh1.metric(label="Cette semaine", value=perf_semaine['dossiers_traites'])
    colh2.metric(label="% hebdo", value=f"{perf_semaine['taux_realisation']:.1f}%")
    colh3.metric(label="Seuil hebdo", value=f"{perf_semaine['seuil_reussite']}")
    
    if perf_semaine['objectif_atteint']:
        colh4.success("🎯 Objectif atteint !")
    else:
        colh4.write(f"Période : {perf_semaine['semaine']}")

def export_analyse(db: DatabaseManager, stats_calc: StatisticsCalculator):
    """Export avec les nouveaux calculs"""
    # Générer le CSV formaté
    kpis = stats_calc.calculer_kpis_globaux()
    traitements = db.obtenir_traitements()
    # Calcul des dates uniques
    dates = set(t['date_traitement'] for t in traitements)
    jours_ecoules = len(dates)
    total_dossiers = kpis['dossiers_traites']
    taux_reussite = kpis['pourcentage_traite']
    stock_restant = kpis['stock_restant']
    objectif = int(db.obtenir_parametre('objectif_journalier') or 200)
    seuil_objectif = float(db.obtenir_parametre('seuil_objectif') or 0.9)
    seuil_journalier = objectif * seuil_objectif  # 180 dossiers
    
    if jours_ecoules > 0:
        taux_journalier_reel = total_dossiers / jours_ecoules
        # Calcul selon la nouvelle logique
        if taux_journalier_reel >= seuil_journalier:
            perf_journalier_pct = (taux_journalier_reel / objectif) * 100
        else:
            perf_journalier_pct = (taux_journalier_reel / seuil_journalier) * 90
        perf_hebdo_pct = perf_journalier_pct
        perf_mensuel_pct = perf_journalier_pct
        perf_annuel_pct = perf_journalier_pct
    else:
        taux_journalier_reel = 0
        perf_journalier_pct = perf_hebdo_pct = perf_mensuel_pct = perf_annuel_pct = 0
    
    actifs = db.obtenir_archivistes()
    nb_archivistes = len(actifs)

    # Section archivistes performance totale (tous traitements)
    perf_arch = stats_calc.obtenir_performances_30j_par_archiviste()

    buffer = StringIO()
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(["=== ANALYSE TABLEAU DE BORD SERVICE ARCHIVES ==="])
    writer.writerow([])
    writer.writerow([" ", " ", " ", " ", " ", " ", " "])  # ligne vide
    writer.writerow(["1. RÉSUMÉ GÉNÉRAL"])
    writer.writerow(["Indicateur", "Valeur"])
    writer.writerow(["Date d'analyse", datetime.now().strftime("%d/%m/%Y %H:%M")])
    writer.writerow(["Stock initial", f"{kpis['stock_initial']}"])
    writer.writerow(["Nombre d'archivistes", f"{nb_archivistes}"])
    writer.writerow(["Objectif journalier", f"{objectif}"])
    writer.writerow(["Seuil d'atteinte (90%)", f"{int(seuil_journalier)}"])
    writer.writerow(["Taux de réussite (%)", f"{taux_reussite:.1f}"])
    writer.writerow(["Dossiers traités total", f"{total_dossiers}"])
    writer.writerow(["Jours écoulés", f"{jours_ecoules}"])
    writer.writerow(["Progression (%)", f"{taux_reussite:.1f}"])
    writer.writerow(["Dossiers restants", f"{stock_restant}"])
    writer.writerow(["Taux journalier réel", f"{taux_journalier_reel:.1f}"])
    writer.writerow(["Performance journalière (%)", f"{perf_journalier_pct:.1f}"])
    writer.writerow(["Performance hebdomadaire (%)", f"{perf_hebdo_pct:.1f}"])
    writer.writerow(["Performance mensuelle (%)", f"{perf_mensuel_pct:.1f}"])
    writer.writerow(["Performance annuelle (%)", f"{perf_annuel_pct:.1f}"])
    writer.writerow([])
    writer.writerow([" ", " ", " ", " ", " ", " ", " "])  # vide
    writer.writerow(["2. PERFORMANCE DES ARCHIVISTES"])
    writer.writerow([
        "Nom", "Dossiers_Traités", "Jours_Travaillés", "Taux_Journalier",
        "Objectif_Individuel", "Seuil_90%", "Performance_%", "Statut"
    ])
    for stat in perf_arch:
        nom = stat['archiviste']
        dossiers_t = stat['total_dossiers']
        jours = stat['jours_travailles']
        taux_j = (dossiers_t / jours) if jours else 0
        objectif_ind = objectif
        seuil_90 = stat['seuil_journalier']
        perf_pct = stat['taux_objectif']
        statut = stat['statut']
        
        writer.writerow([
            nom, f"{dossiers_t}", f"{jours}", f"{taux_j:.1f}",
            f"{objectif_ind}", f"{seuil_90}", f"{perf_pct:.1f}", statut
        ])

    return buffer.getvalue()

def afficher_tableaux(db: DatabaseManager, stats_calc: StatisticsCalculator):
    st.sidebar.subheader("🔍 Filtrer les données par intervalle")
    start_date = st.sidebar.date_input("Date début", value=date.today() - timedelta(days=30))
    end_date = st.sidebar.date_input("Date fin", value=date.today())
    if start_date > end_date:
        st.sidebar.error("La date début doit être antérieure ou égale à la date fin.")
        return
    traitements = db.obtenir_traitements(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Détail des traitements",
        "👥 Hebdo par archiviste",
        "📈 30 derniers jours",
        "📅 Performances annuelles"
    ])
    with tab1:
        st.write(
            f"### Détail des traitements du {start_date.strftime('%d/%m/%Y')} "
            f"au {end_date.strftime('%d/%m/%Y')}"
        )
        if traitements:
            affichage = []
            for t in traitements:
                d = datetime.strptime(t['date_traitement'], "%Y-%m-%d").strftime("%d/%m/%Y")
                affichage.append({
                    "ID": t['id'],
                    "Date": d,
                    "Archiviste": t['archiviste'],
                    "Dossiers": t['dossiers_traites'],
                    "Commentaire": t['commentaire'] or ""
                })
            df_display = pd.DataFrame(affichage)
            st.dataframe(df_display, use_container_width=True)

            csv_buffer = StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["ID", "Date", "Archiviste", "Dossiers", "Commentaire"])
            for row in affichage:
                writer.writerow([
                    row["ID"], row["Date"], row["Archiviste"],
                    row["Dossiers"], row["Commentaire"]
                ])
            st.download_button(
                label="⬇️ Exporter CSV simple",
                data=csv_buffer.getvalue().encode("utf-8-sig"),
                file_name=f"traitements_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Aucun traitement à afficher pour cet intervalle.")

    with tab2:
        st.write("### 🌐 Performances hebdomadaires par archiviste")
        stats_hebdo = stats_calc.obtenir_performances_hebdo_par_archiviste()
        if stats_hebdo:
            affichage = []
            for i, stat in enumerate(stats_hebdo, start=1):
                affichage.append({
                    "Rang": f"#{i}",
                    "Archiviste": stat['archiviste'],
                    "Dossiers": stat['total_dossiers'],
                    "Jours travaillés": stat['jours_travailles'],
                    "Moyenne/J": stat['moyenne_jour'],
                    "% Performance": f"{stat['taux_hebdo']}%",
                    "Seuil (90%)": stat['seuil_reussite'],
                    "État": stat['statut']
                })
            df_h = pd.DataFrame(affichage)
            st.dataframe(df_h, use_container_width=True)
        else:
            st.info("Aucune donnée hebdomadaire pour le moment.")

    with tab3:
        st.write("### 📊 Performances sur 30 derniers jours par archiviste")
        stats_30 = stats_calc.obtenir_performances_30j_par_archiviste()
        if stats_30:
            affichage = []
            for stat in stats_30:
                affichage.append({
                    "Archiviste": stat['archiviste'],
                    "Total": stat['total_dossiers'],
                    "Jours travaillés": stat['jours_travailles'],
                    "Moyenne/J": stat['moyenne_jour'],
                    "% Performance": f"{stat['taux_objectif']}%",
                    "Seuil (90%)": stat['seuil_journalier'],
                    "Statut": stat['statut']
                })
            df_30 = pd.DataFrame(affichage)
            st.dataframe(df_30, use_container_width=True)
        else:
            st.info("Pas assez de données pour calculer les 30 derniers jours.")

    with tab4:
        st.write("### 📅 Performances sur l'année par archiviste")
        
        # Sélecteur d'année
        annee_courante = date.today().year
        col_annee1, col_annee2 = st.columns([1, 3])
        with col_annee1:
            annee_selectee = st.selectbox(
                "Année :", 
                options=list(range(annee_courante - 5, annee_courante + 1)),
                index=5,  # Année courante par défaut
                key="annee_perf"
            )
        
        stats_annee = stats_calc.obtenir_performances_annuelles_par_archiviste(annee_selectee)
        
        if stats_annee:
            # Calculer quelques statistiques globales
            total_dossiers_annee = sum(s['total_dossiers'] for s in stats_annee)
            total_jours_travailles = sum(s['jours_travailles'] for s in stats_annee)
            
            # Afficher un résumé
            col1, col2, col3 = st.columns(3)
            col1.metric("Total dossiers", f"{total_dossiers_annee:,}".replace(",", " "))
            col2.metric("Total jours travaillés", total_jours_travailles)
            col3.metric("Moyenne globale/jour", f"{total_dossiers_annee/total_jours_travailles:.1f}" if total_jours_travailles > 0 else "0")
            
            st.markdown("---")
            
            # Tableau détaillé
            affichage_annee = []
            for i, stat in enumerate(stats_annee, start=1):
                affichage_annee.append({
                    "Rang": f"#{i}",
                    "Archiviste": stat['archiviste'],
                    "Total dossiers": f"{stat['total_dossiers']:,}".replace(",", " "),
                    "Jours travaillés": stat['jours_travailles'],
                    "Moyenne/jour": stat['moyenne_jour'],
                    "% Performance": f"{stat['taux_objectif']}%",
                    "Seuil (90%)": stat['seuil_journalier'],
                    "% Couverture année": f"{stat['couverture_annee']}%",
                    "Statut": stat['statut']
                })
            
            df_annee = pd.DataFrame(affichage_annee)
            st.dataframe(df_annee, use_container_width=True)
            
            # NOUVEAU: Section de modification des saisies depuis le cumul annuel
            st.markdown("---")
            st.subheader("✏️ Modifier des saisies depuis le cumul annuel")
            
            # Sélection d'un archiviste pour voir ses saisies
            archivistes_annee = [s['archiviste'] for s in stats_annee]
            archiviste_selectionne = st.selectbox(
                "Sélectionner un archiviste pour voir/modifier ses saisies :",
                options=archivistes_annee,
                key="archiviste_cumul_annuel"
            )
            
            if archiviste_selectionne:
                # Récupérer les saisies de cet archiviste pour l'année
                date_debut_annee = date(annee_selectee, 1, 1)
                date_fin_annee = date(annee_selectee, 12, 31)
                
                saisies_archiviste = db.obtenir_traitements_par_archiviste(
                    archiviste_selectionne,
                    date_debut_annee.strftime('%Y-%m-%d'),
                    date_fin_annee.strftime('%Y-%m-%d')
                )
                
                if saisies_archiviste:
                    st.write(f"**Saisies de {archiviste_selectionne} en {annee_selectee} :**")
                    
                    # Afficher les saisies dans un tableau avec possibilité de sélection
                    affichage_saisies = []
                    for s in saisies_archiviste:
                        affichage_saisies.append({
                            "ID": s['id'],
                            "Date": datetime.strptime(s['date_traitement'], "%Y-%m-%d").strftime("%d/%m/%Y"),
                            "Dossiers": s['dossiers_traites'],
                            "Commentaire": s['commentaire'] or ""
                        })
                    
                    df_saisies = pd.DataFrame(affichage_saisies)
                    st.dataframe(df_saisies, use_container_width=True)
                    
                    # Sélection d'une saisie à modifier
                    if len(saisies_archiviste) > 0:
                        ids_saisies = [s['id'] for s in saisies_archiviste]
                        id_saisie_modif = st.selectbox(
                            "Choisir une saisie à modifier :",
                            options=ids_saisies,
                            format_func=lambda x: f"ID:{x} - {next((datetime.strptime(s['date_traitement'], '%Y-%m-%d').strftime('%d/%m/%Y') for s in saisies_archiviste if s['id'] == x), '')} - {next((s['dossiers_traites'] for s in saisies_archiviste if s['id'] == x), '')} dossiers",
                            key="id_saisie_modif_cumul"
                        )
                        
                        # Trouver la saisie sélectionnée
                        saisie_selectionnee = next((s for s in saisies_archiviste if s['id'] == id_saisie_modif), None)
                        
                        if saisie_selectionnee:
                            st.markdown("**Modifier cette saisie :**")
                            
                            col_modif1, col_modif2 = st.columns(2)
                            
                            with col_modif1:
                                nouvelle_date_cumul = st.date_input(
                                    "Nouvelle date :",
                                    value=datetime.strptime(saisie_selectionnee['date_traitement'], "%Y-%m-%d").date(),
                                    key="nouvelle_date_cumul"
                                )
                                
                                nouveaux_dossiers_cumul = st.number_input(
                                    "Nouveau nombre de dossiers :",
                                    min_value=0,
                                    value=saisie_selectionnee['dossiers_traites'],
                                    step=1,
                                    key="nouveaux_dossiers_cumul"
                                )
                            
                            with col_modif2:
                                nouveau_commentaire_cumul = st.text_area(
                                    "Nouveau commentaire :",
                                    value=saisie_selectionnee['commentaire'] or "",
                                    height=100,
                                    key="nouveau_commentaire_cumul"
                                )
                            
                            if st.button("✅ Enregistrer les modifications", key="btn_modif_cumul"):
                                try:
                                    with sqlite3.connect(db.db_path) as conn:
                                        cursor = conn.cursor()
                                        cursor.execute("""
                                            UPDATE traitements 
                                            SET date_traitement = ?, dossiers_traites = ?, commentaire = ?
                                            WHERE id = ?
                                        """, (
                                            nouvelle_date_cumul.strftime("%Y-%m-%d"),
                                            nouveaux_dossiers_cumul,
                                            nouveau_commentaire_cumul,
                                            saisie_selectionnee['id']
                                        ))
                                        conn.commit()
                                    
                                    st.success(f"✅ Saisie ID:{saisie_selectionnee['id']} modifiée avec succès !")
                                    st.rerun()  # Actualiser la page
                                    
                                except Exception as e:
                                    st.error(f"❌ Erreur lors de la modification : {e}")
                else:
                    st.info(f"Aucune saisie trouvée pour {archiviste_selectionne} en {annee_selectee}.")
            
            # Option d'export pour les données annuelles
            if st.button("⬇️ Exporter performances annuelles CSV"):
                csv_buffer = StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow([
                    "Rang", "Archiviste", "Total_dossiers", "Jours_travailles", 
                    "Moyenne_jour", "Taux_performance", "Seuil_90", "Couverture_annee", "Statut"
                ])
                for row in affichage_annee:
                    writer.writerow([
                        row["Rang"], row["Archiviste"], 
                        row["Total dossiers"].replace(" ", ""),
                        row["Jours travaillés"], row["Moyenne/jour"],
                        row["% Performance"], row["Seuil (90%)"],
                        row["% Couverture année"], row["Statut"]
                    ])
                
                st.download_button(
                    label="Télécharger performances annuelles",
                    data=csv_buffer.getvalue().encode("utf-8-sig"),
                    file_name=f"performances_annuelles_{annee_selectee}.csv",
                    mime="text/csv"
                )
                
        else:
            st.info(f"Aucune donnée disponible pour l'année {annee_selectee}.")

    # Bouton d'export d'analyse complet existant
    st.markdown("---")
    if st.button("⬇️ Exporter Analyse CSV complet"):
        csv_data = export_analyse(db, stats_calc)
        st.download_button(
            label="Télécharger fichier d'analyse",
            data=csv_data.encode("latin1"),
            file_name=f"analyse_archives_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

def page_parametres(db: DatabaseManager):
    """Page paramètres avec seuil d'objectif"""
    st.header("⚙️ Paramètres de l'application")
    stock_init = db.obtenir_parametre('stock_initial')
    obj = db.obtenir_parametre('objectif_journalier')
    seuil = db.obtenir_parametre('seuil_objectif')
    pwd = db.obtenir_parametre('mot_de_passe')
    pwd_app = db.obtenir_parametre('mot_de_passe_app')
    
    col1, col2 = st.columns(2)
    with col1:
        new_stock = st.number_input(
            "Stock initial de dossiers :",
            min_value=0,
            value=int(stock_init or 0),
            step=1000
        )
    with col2:
        new_obj = st.number_input(
            "Objectif journalier :",
            min_value=0,
            value=int(obj or 200),
            step=10
        )
    
    # Paramètre seuil d'objectif
    col_seuil, col_info = st.columns([1, 2])
    with col_seuil:
        new_seuil = st.slider(
            "Seuil d'objectif atteint (%) :",
            min_value=0.5,
            max_value=1.0,
            value=float(seuil or 0.9),
            step=0.05,
            help="Pourcentage de l'objectif à partir duquel il est considéré comme atteint"
        )
    with col_info:
        seuil_dossiers = int(new_obj * new_seuil)
        st.info(f"**Avec ces paramètres :**\n- Objectif : {new_obj} dossiers/jour\n- Seuil d'atteinte : {seuil_dossiers} dossiers ({new_seuil*100:.0f}%)")
    
    col3, col4 = st.columns(2)
    with col3:
        new_pwd = st.text_input(
            "Mot de passe administration :",
            value=pwd or "",
            type="password"
        )
    with col4:
        new_pwd_app = st.text_input(
            "Mot de passe application :",
            value=pwd_app or "",
            type="password"
        )
    
    if st.button("✅ Enregistrer les paramètres"):
        if new_stock <= 0 or new_obj <= 0:
            st.error("Le stock initial et l'objectif journalier doivent être strictement positifs.")
        elif len(new_pwd) < 3 or len(new_pwd_app) < 3:
            st.error("Les mots de passe doivent contenir au moins 3 caractères.")
        else:
            db.mettre_a_jour_parametre('stock_initial', str(new_stock))
            db.mettre_a_jour_parametre('objectif_journalier', str(new_obj))
            db.mettre_a_jour_parametre('seuil_objectif', str(new_seuil))
            db.mettre_a_jour_parametre('mot_de_passe', new_pwd)
            db.mettre_a_jour_parametre('mot_de_passe_app', new_pwd_app)
            st.success("✅ Paramètres mis à jour.")

def page_archivistes(db: DatabaseManager):
    st.header("👥 Gestion des archivistes CNA")
    all_arch = db.obtenir_archivistes(actifs_seulement=False)
    affichage = []
    for nom, actif in all_arch:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(date_traitement) FROM traitements WHERE archiviste = ?",
                (nom,)
            )
            last = cursor.fetchone()[0]
        if last:
            try:
                d = datetime.strptime(last, "%Y-%m-%d").strftime("%d/%m/%Y")
            except:
                d = "Inconnue"
        else:
            d = "Jamais"
        statut = "✅ Actif" if actif else "❌ Inactif"
        affichage.append({"Nom": nom, "Statut": statut, "Dernière activité": d})
    df_arch = pd.DataFrame(affichage)
    st.dataframe(df_arch, use_container_width=True)

    st.subheader("➕ Ajouter un nouvel archiviste")
    new_arch = st.text_input("Nom complet (MAJUSCULES) :", "")
    if st.button("➕ Ajouter archiviste"):
        if not new_arch.strip():
            st.error("Le nom ne peut pas être vide.")
        else:
            try:
                db.ajouter_archiviste(new_arch.strip().upper())
                st.success(f"✅ Archiviste {new_arch.strip().upper()} ajouté.")
            except sqlite3.IntegrityError:
                st.warning(f"⚠️ L'archiviste {new_arch.strip().upper()} existe déjà.")
            except Exception as e:
                st.error(f"❌ Impossible d'ajouter : {e}")

    st.markdown("---")
    st.subheader("🔧 Mettre à jour / Supprimer")
    choix_arch = st.selectbox(
        "Sélectionner archiviste :",
        options=[a[0] for a in all_arch]
    )
    actif_status = next((a[1] for a in all_arch if a[0] == choix_arch), 1)
    col1, col2 = st.columns(2)
    with col1:
        if actif_status:
            if st.button("Désactiver archiviste"):
                db.desactiver_archiviste(choix_arch)
                st.success(f"✅ Archiviste {choix_arch} désactivé.")
        else:
            if st.button("Réactiver archiviste"):
                with sqlite3.connect(db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE archivistes SET actif = 1 WHERE nom = ?", (choix_arch,))
                    conn.commit()
                st.success(f"✅ Archiviste {choix_arch} réactivé.")
    with col2:
        if st.button("Supprimer définitivement"):
            confirm = st.checkbox(f"⚠️ Confirmer la suppression de {choix_arch}")
            if confirm:
                try:
                    db.supprimer_archiviste(choix_arch)
                    st.success(f"✅ Archiviste {choix_arch} supprimé.")
                except Exception as e:
                    st.error(f"❌ Impossible de supprimer : {e}")

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
    
    # Afficher les paramètres actuels dans la sidebar
    objectif = int(db.obtenir_parametre('objectif_journalier') or 200)
    seuil = float(db.obtenir_parametre('seuil_objectif') or 0.9)
    seuil_dossiers = int(objectif * seuil)
    
    st.sidebar.info(f"""
    **Paramètres actuels :**
    - Objectif : {objectif} dossiers/jour
    - Seuil : {seuil_dossiers} dossiers ({seuil*100:.0f}%)
    """)
    
    section = st.sidebar.radio(
        "Navigation",
        ("🏠 Accueil", "➕ Nouvelle saisie", "📊 Vue d'ensemble", "📋 Détail", "⚙️ Paramètres", "👥 Archivistes")
    )

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
            📝 Enregistrer, modifier ou supprimer des traitements de dossiers physiques
            
            **📊 Vue d'ensemble**  
            📈 Consulter les KPIs et performances globales (avec seuil 90%)
            
            **📋 Détail**  
            📊 Historique des traitements et performances par archiviste
            """)
        
        with col2:
            st.markdown("""
            **⚙️ Paramètres**  
            🔧 Configurer stock initial, objectifs, seuil & mots de passe
            
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
            • Modification et suppression de saisies
            • Calcul automatique des jours ouvrés
            • Suivi en temps réel des dossiers traités
            """)
        
        with col2:
            st.success("""
            **📈 Performances**
            
            • Objectif : 200 dossiers/jour
            • Seuil d'atteinte : 180 dossiers (90%)
            • Analyse hebdomadaire, mensuelle, annuelle
            • Modification depuis le cumul annuel
            """)
        
        with col3:
            st.warning("""
            **🎯 Objectifs**
            
            • Suivi des objectifs journaliers
            • Progression globale avec seuil 90%
            • Gestion individuelle des saisies
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
                label="🎯 Seuil quotidien", 
                value=f"{seuil_dossiers} dossiers"
            )

        # Sidebar admin
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

if __name__ == "__main__":
    main()
