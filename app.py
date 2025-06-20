import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta, date
import os
import csv
import hashlib
import json

# Configuration de la page
st.set_page_config(
    page_title="Application de Pointage", 
    layout="wide",
    initial_sidebar_state="auto"
)

# Configuration Admin
ADMIN_USERNAME = "clinique"
ADMIN_PASSWORD = "clinique2021"
ADMIN_NOM = "Admin"
ADMIN_PRENOM = "Systeme"

# Définir les colonnes pour chaque fichier CSV
UTILISATEURS_COLUMNS = ["ID", "Username", "Password", "Nom", "Prenom", "Role", "Actif"]
EMPLOYES_COLUMNS = ["ID", "Nom", "Prenom", "Service", "Heure_Entree", "Heure_Sortie", "Actif", "Poste"]  # Ajout de "Poste"
POINTAGES_COLUMNS = ["ID", "Nom", "Prenom", "Service", "Type", "Heure", "Date", "Statut"]
RETARDS_COLUMNS = ["ID", "Nom", "Prenom", "Service", "Heure_Arrivee", "Heure_Officielle", "Retard_min", "Retard_affichage", "Date"]
ABSENCES_COLUMNS = ["ID", "Nom", "Prenom", "Service", "Date", "Type", "Justification"]

# Services disponibles
SERVICES_DISPONIBLES = [
    "Administration",
    "Reception",
    "Urgence",
    "Radiologie",
    "Reanimation",
    "Pharmacie"
]

# Fonction de hachage de mot de passe
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def save_data_to_csv():
    """Sauvegarde toutes les données dans des fichiers CSV"""
    try:
        st.session_state.utilisateurs.to_csv('utilisateurs.csv', index=False)
        st.session_state.employes.to_csv('employes.csv', index=False)
        st.session_state.pointages.to_csv('pointages.csv', index=False)
        st.session_state.retards.to_csv('retards.csv', index=False)
        st.session_state.absences.to_csv('absences.csv', index=False)
        
        # Sauvegarder la configuration
        config = {
            "HEURE_ENTREE_DEFAUT": st.session_state.HEURE_ENTREE_DEFAUT.strftime("%H:%M"),
            "HEURE_SORTIE_DEFAUT": st.session_state.HEURE_SORTIE_DEFAUT.strftime("%H:%M"),
            "SEUIL_RETARD": st.session_state.SEUIL_RETARD
        }
        with open('config.json', 'w') as f:
            json.dump(config, f)
            
        return True
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde: {str(e)}")
        return False

def load_data_from_csv():
    """Charge les données depuis les fichiers CSV"""
    try:
        # Initialiser les DataFrames avec les colonnes appropriées
        dfs = {
            'utilisateurs': pd.DataFrame(columns=UTILISATEURS_COLUMNS),
            'employes': pd.DataFrame(columns=EMPLOYES_COLUMNS),
            'pointages': pd.DataFrame(columns=POINTAGES_COLUMNS),
            'retards': pd.DataFrame(columns=RETARDS_COLUMNS),
            'absences': pd.DataFrame(columns=ABSENCES_COLUMNS)
        }
        
        # Charger ou créer les fichiers
        for file in dfs.keys():
            file_path = f'{file}.csv'
            if not os.path.exists(file_path):
                # Créer le fichier avec l'admin si c'est utilisateurs.csv
                if file == 'utilisateurs':
                    dfs[file] = pd.DataFrame([{
                        "ID": 1,
                        "Username": ADMIN_USERNAME,
                        "Password": hash_password(ADMIN_PASSWORD),
                        "Nom": ADMIN_NOM,
                        "Prenom": ADMIN_PRENOM,
                        "Role": "admin",
                        "Actif": True
                    }])
                    dfs[file].to_csv(file_path, index=False)
                else:
                    pd.DataFrame(columns=globals()[f'{file.upper()}_COLUMNS']).to_csv(file_path, index=False)
            else:
                dfs[file] = pd.read_csv(file_path)
                # Vérifier que toutes les colonnes existent
                for col in globals()[f'{file.upper()}_COLUMNS']:
                    if col not in dfs[file].columns:
                        dfs[file][col] = None
                # Réorganiser les colonnes
                dfs[file] = dfs[file][globals()[f'{file.upper()}_COLUMNS']]
        
        # Charger la configuration
        config = {
            "HEURE_ENTREE_DEFAUT": time(8, 0),
            "HEURE_SORTIE_DEFAUT": time(17, 0),
            "SEUIL_RETARD": 15
        }
        
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                saved_config = json.load(f)
                config["HEURE_ENTREE_DEFAUT"] = datetime.strptime(saved_config["HEURE_ENTREE_DEFAUT"], "%H:%M").time()
                config["HEURE_SORTIE_DEFAUT"] = datetime.strptime(saved_config["HEURE_SORTIE_DEFAUT"], "%H:%M").time()
                config["SEUIL_RETARD"] = saved_config["SEUIL_RETARD"]
        
        # Stocker dans session_state
        for key, df in dfs.items():
            st.session_state[key] = df
        
        st.session_state.update({
            "HEURE_ENTREE_DEFAUT": config["HEURE_ENTREE_DEFAUT"],
            "HEURE_SORTIE_DEFAUT": config["HEURE_SORTIE_DEFAUT"],
            "SEUIL_RETARD": config["SEUIL_RETARD"]
        })
        
        return True
    except Exception as e:
        st.error(f"Erreur lors du chargement: {str(e)}")
        return False

# Vérification de l'utilisateur
def verify_user(username, password):
    users = st.session_state.utilisateurs
    user = users[(users["Username"] == username) & (users["Actif"] == True)]
    
    if user.empty:
        return False
    
    hashed_input = hash_password(password)
    stored_hash = user.iloc[0]["Password"]
    
    return hashed_input == stored_hash

# Convertir string en time
def str_to_time(time_str):
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except:
        return st.session_state.HEURE_ENTREE_DEFAUT

# Fonction pour calculer les retards
def calculer_retard(id_employe, heure_arrivee):
    employe = st.session_state.employes[st.session_state.employes["ID"] == id_employe].iloc[0]
    heure_officielle = str_to_time(employe["Heure_Entree"])
    
    # Convertir en datetime pour faciliter les calculs
    arrivee_dt = datetime.combine(date.today(), heure_arrivee)
    officielle_dt = datetime.combine(date.today(), heure_officielle)
    
    # Calculer la différence en minutes
    retard_min = (arrivee_dt - officielle_dt).total_seconds() / 60
    
    if retard_min > st.session_state.SEUIL_RETARD:
        # Formater l'affichage du retard
        if retard_min >= 60:
            heures = int(retard_min // 60)
            minutes = int(retard_min % 60)
            retard_affichage = f"{heures}h{minutes:02d}"
        else:
            retard_affichage = f"{int(retard_min)}min"
        
        # Enregistrer le retard
        df_retards = st.session_state.retards
        new_retard = pd.DataFrame([[id_employe, employe["Nom"], employe["Prenom"], employe["Service"], 
                                 heure_arrivee.strftime("%H:%M"), heure_officielle.strftime("%H:%M"), 
                                 retard_min, retard_affichage, date.today().strftime("%Y-%m-%d")]],
                               columns=RETARDS_COLUMNS)
        st.session_state.retards = pd.concat([df_retards, new_retard], ignore_index=True)
        save_data_to_csv()
        
        return retard_affichage
    return None

# Fonctions de gestion du personnel
def ajouter_employe(nom, prenom, service, poste, heure_entree=None, heure_sortie=None, actif=True):
    df = st.session_state.employes
    new_id = df["ID"].max() + 1 if not df.empty else 1
    
    # Définir les heures par défaut selon le poste
    if heure_entree is None:
        heure_entree = time(8, 0) if poste == "Jour" else time(20, 0)
    if heure_sortie is None:
        heure_sortie = time(17, 0) if poste == "Jour" else time(5, 0)
    
    new_employe = pd.DataFrame([[new_id, nom, prenom, service, heure_entree.strftime("%H:%M"), 
                              heure_sortie.strftime("%H:%M"), actif, poste]], 
                            columns=EMPLOYES_COLUMNS)
    st.session_state.employes = pd.concat([df, new_employe], ignore_index=True)
    save_data_to_csv()
    st.success(f"Employé {prenom} {nom} ({poste}) ajouté avec succès!")

def modifier_employe(id_employe, nom=None, prenom=None, service=None, poste=None, heure_entree=None, heure_sortie=None, actif=None):
    df = st.session_state.employes
    idx = df[df["ID"] == id_employe].index[0]
    
    if nom: df.at[idx, "Nom"] = nom
    if prenom: df.at[idx, "Prenom"] = prenom
    if service: df.at[idx, "Service"] = service
    if poste: df.at[idx, "Poste"] = poste
    if heure_entree: 
        heure_entree = heure_entree.time() if isinstance(heure_entree, datetime) else heure_entree
        df.at[idx, "Heure_Entree"] = heure_entree.strftime("%H:%M")
    if heure_sortie: 
        heure_sortie = heure_sortie.time() if isinstance(heure_sortie, datetime) else heure_sortie
        df.at[idx, "Heure_Sortie"] = heure_sortie.strftime("%H:%M")
    if actif is not None: df.at[idx, "Actif"] = actif
    
    st.session_state.employes = df
    save_data_to_csv()
    st.success("Employé modifié avec succès!")

def supprimer_employe(id_employe):
    df = st.session_state.employes
    st.session_state.employes = df[df["ID"] != id_employe]
    save_data_to_csv()
    st.success("Employé supprimé avec succès!")

# Fonctions de pointage
def pointer(id_employe, type_pointage):
    employes = st.session_state.employes
    employe = employes[employes["ID"] == id_employe].iloc[0]
    
    now = datetime.now()
    heure_actuelle = now.time()
    date_actuelle = now.date()
    
    # Enregistrement du pointage
    df_pointage = st.session_state.pointages
    new_pointage = pd.DataFrame([[id_employe, employe["Nom"], employe["Prenom"], employe["Service"], 
                               type_pointage, heure_actuelle.strftime("%H:%M"), 
                               date_actuelle.strftime("%Y-%m-%d"), "Présent"]],
                            columns=POINTAGES_COLUMNS)
    st.session_state.pointages = pd.concat([df_pointage, new_pointage], ignore_index=True)
    
    if type_pointage == "Entrée":
        # Vérification des retards
        retard = calculer_retard(id_employe, heure_actuelle)
        if retard:
            st.warning(f"Retard enregistré: {retard}")
    
    save_data_to_csv()
    st.success(f"Pointage {type_pointage} enregistré avec succès!")

# Vérifier les employés non pointés
def check_missing_employees():
    today = date.today().strftime("%Y-%m-%d")
    employes = st.session_state.employes
    pointages = st.session_state.pointages
    
    if pointages.empty:
        return employes[employes["Actif"] == True], pd.DataFrame()
    
    employes_actifs = employes[employes["Actif"] == True]
    pointages_auj = pointages[pointages["Date"] == today]
    
    sans_entree = employes_actifs[~employes_actifs["ID"].isin(
        pointages_auj[pointages_auj["Type"] == "Entrée"]["ID"]
    )]
    
    avec_entree = pointages_auj[
        (pointages_auj["Type"] == "Entrée") & 
        (~pointages_auj["ID"].isin(pointages_auj[pointages_auj["Type"] == "Sortie"]["ID"]))
    ]["ID"]
    
    sans_sortie = employes_actifs[employes_actifs["ID"].isin(avec_entree)]
    
    return sans_entree, sans_sortie

# Marquer une absence
def marquer_absence(id_employe, date_absence, type_absence, justification=""):
    employes = st.session_state.employes
    employe = employes[employes["ID"] == id_employe].iloc[0]
    
    df_absences = st.session_state.absences
    new_absence = pd.DataFrame([[id_employe, employe["Nom"], employe["Prenom"], employe["Service"], 
                              date_absence.strftime("%Y-%m-%d"), type_absence, justification]],
                            columns=ABSENCES_COLUMNS)
    st.session_state.absences = pd.concat([df_absences, new_absence], ignore_index=True)
    save_data_to_csv()
    
    df_pointage = st.session_state.pointages
    today_pointage = df_pointage[(df_pointage["ID"] == id_employe) & 
                               (df_pointage["Date"] == date_absence.strftime("%Y-%m-%d"))]
    
    if today_pointage.empty:
        new_pointage = pd.DataFrame([[id_employe, employe["Nom"], employe["Prenom"], employe["Service"], 
                                   "Absence", "", date_absence.strftime("%Y-%m-%d"), type_absence]],
                                 columns=POINTAGES_COLUMNS)
        st.session_state.pointages = pd.concat([df_pointage, new_pointage], ignore_index=True)
        save_data_to_csv()

# Calculer les heures travaillées
def calculer_heures_travaillees(id_employe, date):
    pointages = st.session_state.pointages
    pointages_date = pointages[(pointages["ID"] == id_employe) & 
                             (pointages["Date"] == date.strftime("%Y-%m-%d")) &
                             (pointages["Statut"] == "Présent")]
    
    entrees = pointages_date[pointages_date["Type"] == "Entrée"]["Heure"].sort_values()
    sorties = pointages_date[pointages_date["Type"] == "Sortie"]["Heure"].sort_values()
    
    if len(entrees) == 0 or len(sorties) == 0:
        return timedelta(0)
    
    premiere_entree = str_to_time(entrees.iloc[0])
    derniere_sortie = str_to_time(sorties.iloc[-1])
    
    return datetime.combine(date, derniere_sortie) - datetime.combine(date, premiere_entree)

# Fonctions de gestion des utilisateurs
def ajouter_utilisateur(username, password, nom, prenom, role):
    df = st.session_state.utilisateurs
    
    # Vérifier si l'utilisateur existe déjà
    if not df[df["Username"] == username].empty:
        st.error("Ce nom d'utilisateur existe déjà")
        return False
    
    new_id = df["ID"].max() + 1 if not df.empty else 2  # Commencer à 2 car admin est 1
    
    hashed_password = hash_password(password)
    new_user = pd.DataFrame([[new_id, username, hashed_password, nom, prenom, role, True]], 
                          columns=UTILISATEURS_COLUMNS)
    st.session_state.utilisateurs = pd.concat([df, new_user], ignore_index=True)
    save_data_to_csv()
    st.success(f"Utilisateur {username} ajouté avec succès!")
    return True

def modifier_utilisateur(id_user, username=None, password=None, nom=None, prenom=None, role=None, actif=None):
    df = st.session_state.utilisateurs
    idx = df[df["ID"] == id_user].index[0]
    
    if username: df.at[idx, "Username"] = username
    if password: df.at[idx, "Password"] = hash_password(password)
    if nom: df.at[idx, "Nom"] = nom
    if prenom: df.at[idx, "Prenom"] = prenom
    if role: df.at[idx, "Role"] = role
    if actif is not None: df.at[idx, "Actif"] = actif
    
    st.session_state.utilisateurs = df
    save_data_to_csv()
    st.success("Utilisateur modifié avec succès!")

def supprimer_utilisateur(id_user):
    df = st.session_state.utilisateurs
    if id_user == 1:
        st.error("Impossible de supprimer l'administrateur principal")
        return
    
    st.session_state.utilisateurs = df[df["ID"] != id_user]
    save_data_to_csv()
    st.success("Utilisateur supprimé avec succès!")

# Interface d'authentification
def login_page():
    st.title("Connexion")
    
    with st.form("login_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        
        if st.form_submit_button("Se connecter"):
            if verify_user(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                user = st.session_state.utilisateurs[st.session_state.utilisateurs["Username"] == username].iloc[0]
                st.session_state["role"] = user["Role"]
                st.rerun()
            else:
                st.error("Identifiants incorrects. Essayez avec admin/admin123")

# Fonction pour afficher les statistiques des retards
def afficher_statistiques_retards(retards):
    if not retards.empty:
        st.subheader("Statistiques des Retards")
        
        # Calculer les métriques
        total_retards = len(retards)
        avg_retard = retards["Retard_min"].mean()
        max_retard = retards["Retard_min"].max()
        
        # Trouver l'employé le plus souvent en retard
        frequent_late = retards.groupby(["Nom", "Prenom", "Service"]).size().idxmax()
        frequent_late_str = f"{frequent_late[1]} {frequent_late[0]} ({frequent_late[2]})"
        
        # Afficher les métriques
        cols = st.columns(4)
        with cols[0]:
            st.metric("Nombre total de retards", total_retards)
        with cols[1]:
            st.metric("Retard moyen", f"{int(avg_retard)} min")
        with cols[2]:
            st.metric("Retard maximum", f"{int(max_retard)} min")
        with cols[3]:
            st.metric("Plus fréquemment en retard", frequent_late_str)
        
        # Graphique des retards par service
        st.subheader("Répartition des retards par service")
        retards_par_service = retards.groupby("Service").size()
        st.bar_chart(retards_par_service)
        
        # Graphique des retards dans le temps
        st.subheader("Évolution des retards dans le temps")
        retards["Date"] = pd.to_datetime(retards["Date"])
        retards_par_date = retards.groupby("Date").size()
        st.line_chart(retards_par_date)
    else:
        st.info("Aucun retard enregistré")

# Interface principale
def main_app():
    st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    """, unsafe_allow_html=True)

    st.title("📝 Application de Pointage Avancée")
    st.sidebar.title(f"Bienvenue, {st.session_state.get('username', 'Admin')}")

    # Menu différent selon le rôle
    if st.session_state.get("role") == "admin":
        menu_options = ["Pointage", "Gestion du Personnel", "Historique", "Retards", "Statistiques", "Administration"]
    elif st.session_state.get("role") == "manager":
        menu_options = ["Pointage", "Gestion du Personnel", "Historique", "Retards", "Statistiques"]
    else:
        menu_options = ["Pointage", "Historique"]

    menu = st.sidebar.selectbox("Menu", menu_options)

    # Affichage des employés non pointés (sauf en Administration)
    if menu != "Administration":
        sans_entree, sans_sortie = check_missing_employees()
        if not sans_entree.empty or not sans_sortie.empty:
            with st.sidebar:
                st.warning("Employés non pointés aujourd'hui :")
                if not sans_entree.empty:
                    st.write("Sans entrée :")
                    for _, emp in sans_entree.iterrows():
                        st.write(f"- {emp['Prenom']} {emp['Nom']}")
                if not sans_sortie.empty:
                    st.write("Sans sortie :")
                    for _, emp in sans_sortie.iterrows():
                        st.write(f"- {emp['Prenom']} {emp['Nom']}")

    # --- SECTION POINTAGE ---
    if menu == "Pointage":
        st.header("Enregistrement des pointages")
        employes = st.session_state.employes
        employes = employes[employes["Actif"] == True]

        if employes.empty:
            st.warning("Aucun employé actif enregistré.")
            return

        # Barre de recherche améliorée
        search_term = st.text_input("Rechercher un employé (nom, prénom ou service)")
        if search_term:
            employes_filtres = employes[
                employes["Nom"].str.contains(search_term, case=False) |
                employes["Prenom"].str.contains(search_term, case=False) |
                employes["Service"].str.contains(search_term, case=False)
            ]
        else:
            employes_filtres = employes

        if employes_filtres.empty:
            st.warning("Aucun employé trouvé avec ce critère de recherche.")
            return

        selected_emp = st.selectbox(
            "Sélectionnez un employé",
            employes_filtres["Prenom"] + " " + employes_filtres["Nom"] + " (" + employes_filtres["Service"] + ")"
        )

        selected_id = employes_filtres[
            (employes_filtres["Prenom"] + " " + employes_filtres["Nom"] + " (" + employes_filtres["Service"] + ")") == selected_emp
        ]["ID"].iloc[0]

        employe = employes[employes["ID"] == selected_id].iloc[0]
        st.info(f"""
        **Service:** {employe['Service']}  
        **Heure d'entrée officielle:** {employe['Heure_Entree']}  
        **Heure de sortie officielle:** {employe['Heure_Sortie']}
        """)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🟢 Enregistrer l'arrivée", use_container_width=True):
                pointer(selected_id, "Entrée")
        with col2:
            if st.button("🔴 Enregistrer la sortie", use_container_width=True):
                pointer(selected_id, "Sortie")
        with col3:
            if st.button("⚠️ Déclarer une absence", use_container_width=True):
                st.session_state["show_absence_form"] = selected_id

        if st.session_state.get("show_absence_form") == selected_id:
            with st.form(f"absence_form_{selected_id}"):
                st.subheader(f"Déclarer une absence pour {employe['Prenom']} {employe['Nom']}")
                type_absence = st.selectbox("Type d'absence", ["Maladie", "Congé", "Autre"])
                justification = st.text_area("Justification (facultatif)")

                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("Confirmer")
                    if submitted:
                        marquer_absence(selected_id, date.today(), type_absence, justification)
                        st.session_state["show_absence_form"] = None
                        st.success("Absence enregistrée avec succès!")
                        st.rerun()
                with col2:
                    canceled = st.form_submit_button("Annuler")
                    if canceled:
                        st.session_state["show_absence_form"] = None
                        st.rerun()

        st.subheader("Derniers pointages")
        pointages = st.session_state.pointages
        if not pointages.empty:
            pointages_recent = pointages.sort_values(by=["Date", "Heure"], ascending=False).head(5)
            st.dataframe(pointages_recent, use_container_width=True)

    # --- SECTION GESTION DU PERSONNEL ---
    elif menu == "Gestion du Personnel":
        if st.session_state.get("role") not in ["admin", "manager"]:
            st.warning("Vous n'avez pas les permissions nécessaires pour accéder à cette section")
            return

        st.header("Gestion du Personnel")

        tab1, tab2, tab3 = st.tabs(["Ajouter Employé", "Modifier Employé", "Supprimer/Désactiver Employé"])

        with tab1:  # Onglet "Ajouter Employé"
            with st.form("ajout_form"):
                col1, col2 = st.columns(2)
                with col1:
                    nom = st.text_input("Nom*")
                with col2:
                    prenom = st.text_input("Prénom*")
                
                col3, col4 = st.columns(2)
                with col3:
                    service = st.selectbox("Service*", SERVICES_DISPONIBLES)
                with col4:
                    poste = st.selectbox("Poste*", ["Jour", "Nuit"])
                
                # Heures par défaut selon le poste
                heure_defaut_entree = time(8, 0) if poste == "Jour" else time(20, 0)
                heure_defaut_sortie = time(17, 0) if poste == "Jour" else time(5, 0)
                
                col5, col6 = st.columns(2)
                with col5:
                    heure_entree = st.time_input("Heure d'entrée*", value=heure_defaut_entree)
                with col6:
                    heure_sortie = st.time_input("Heure de sortie*", value=heure_defaut_sortie)
                
                if st.form_submit_button("Ajouter", use_container_width=True):
                    if nom and prenom:
                        ajouter_employe(nom, prenom, service, poste, heure_entree, heure_sortie)
                        st.rerun()
                    else:
                        st.error("Veuillez remplir tous les champs obligatoires (*)")

        with tab2:
            employes = st.session_state.employes
            if employes.empty:
                st.warning("Aucun employé à modifier")
            else:
                search_term = st.text_input("Rechercher un employé à modifier")
                if search_term:
                    employes_filtres = employes[
                        employes["Nom"].str.contains(search_term, case=False) |
                        employes["Prenom"].str.contains(search_term, case=False) |
                        employes["Service"].str.contains(search_term, case=False)
                    ]
                else:
                    employes_filtres = employes

                if employes_filtres.empty:
                    st.warning("Aucun employé trouvé avec ce critère de recherche")
                else:
                    selected = st.selectbox(
                        "Employé à modifier",
                        employes_filtres["ID"].astype(str) + " - " + employes_filtres["Prenom"] + " " + employes_filtres["Nom"] + " (" + employes_filtres["Service"] + ")"
                    )
                    selected_id = int(selected.split(" - ")[0])
                    employe = employes[employes["ID"] == selected_id].iloc[0]

                    with st.form("modif_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_nom = st.text_input("Nom*", value=employe["Nom"])
                        with col2:
                            new_prenom = st.text_input("Prénom*", value=employe["Prenom"])

                        try:
                            index_service = SERVICES_DISPONIBLES.index(employe["Service"])
                        except ValueError:
                            index_service = 0

                        col3, col4 = st.columns(2)
                        with col3:
                            new_service = st.selectbox("Service*", SERVICES_DISPONIBLES, index=index_service)
                        with col4:
                            new_poste = st.selectbox("Poste*", ["Jour", "Nuit"], index=0 if employe.get("Poste", "Jour") == "Jour" else 1)

                        new_heure_entree = st.time_input("Heure d'entrée*", value=str_to_time(employe["Heure_Entree"]))
                        new_heure_sortie = st.time_input("Heure de sortie*", value=str_to_time(employe["Heure_Sortie"]))
                        new_actif = st.checkbox("Actif", value=employe.get("Actif", True))

                        if st.form_submit_button("Modifier", use_container_width=True):
                            modifier_employe(selected_id, new_nom, new_prenom, new_service, new_poste,
                                             new_heure_entree, new_heure_sortie, new_actif)
                            st.rerun()

        with tab3:
            employes = st.session_state.employes
            if employes.empty:
                st.warning("Aucun employé à supprimer")
            else:
                search_term = st.text_input("Rechercher un employé à supprimer/désactiver")
                if search_term:
                    employes_filtres = employes[
                        employes["Nom"].str.contains(search_term, case=False) |
                        employes["Prenom"].str.contains(search_term, case=False) |
                        employes["Service"].str.contains(search_term, case=False)
                    ]
                else:
                    employes_filtres = employes

                if employes_filtres.empty:
                    st.warning("Aucun employé trouvé avec ce critère de recherche")
                else:
                    to_delete = st.selectbox(
                        "Employé à supprimer/désactiver",
                        employes_filtres["ID"].astype(str) + " - " + employes_filtres["Prenom"] + " " + employes_filtres["Nom"] + " (" + employes_filtres["Service"] + ")"
                    )
                    selected_id = int(to_delete.split(" - ")[0])
                    employe = employes[employes["ID"] == selected_id].iloc[0]

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Désactiver l'employé", use_container_width=True, key=f"desactiver_{selected_id}"):
                            modifier_employe(selected_id, actif=False)
                            st.success("Employé désactivé avec succès!")
                            st.rerun()
                    with col2:
                        if st.button("Supprimer définitivement", use_container_width=True, type="primary", key=f"supprimer_{selected_id}"):
                            supprimer_employe(selected_id)
                            st.success("Employé supprimé avec succès!")
                            st.rerun()

        st.subheader("Liste des Employés")
        employes = st.session_state.employes
        st.dataframe(employes, use_container_width=True)

    # --- SECTION HISTORIQUE ---
    elif menu == "Historique":
        st.header("Historique des Pointages")

        employes = st.session_state.employes

        col1, col2, col3 = st.columns(3)
        with col1:
            selected_service = st.selectbox("Filtrer par service", ["Tous"] + SERVICES_DISPONIBLES)
        with col2:
            date_filter = st.date_input("Filtrer par date")
        with col3:
            statut_filter = st.selectbox("Filtrer par statut", ["Tous", "Présent", "Maladie", "Congé", "Autre"])

        pointages = st.session_state.pointages
        if not pointages.empty:
            if selected_service != "Tous":
                pointages = pointages[pointages["Service"] == selected_service]
            if date_filter:
                pointages = pointages[pointages["Date"] == date_filter.strftime("%Y-%m-%d")]
            if statut_filter != "Tous":
                pointages = pointages[pointages["Statut"] == statut_filter]

            st.dataframe(
                pointages.sort_values(by=["Date", "Heure"], ascending=False),
                use_container_width=True,
                column_config={
                    "Heure": st.column_config.TimeColumn("Heure", format="HH:mm"),
                    "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY")
                }
            )

            st.download_button(
                label="Exporter en CSV",
                data=pointages.to_csv(index=False).encode('utf-8'),
                file_name=f"pointages_{date.today()}.csv",
                mime="text/csv"
            )
        else:
            st.warning("Aucun pointage enregistré")

    # --- SECTION RETARDS ---
    elif menu == "Retards":
        st.header("Historique des Retards")

        col1, col2 = st.columns(2)
        with col1:
            selected_service = st.selectbox("Filtrer par service", ["Tous"] + SERVICES_DISPONIBLES)
        with col2:
            date_filter = st.date_input("Filtrer par date")

        retards = st.session_state.retards
        if not retards.empty:
            if selected_service != "Tous":
                retards = retards[retards["Service"] == selected_service]
            if date_filter:
                retards = retards[retards["Date"] == date_filter.strftime("%Y-%m-%d")]

            st.dataframe(
                retards[["Nom", "Prenom", "Service", "Heure_Arrivee",
                         "Heure_Officielle", "Retard_affichage", "Date"]]
                .sort_values(by=["Date", "Heure_Arrivee"], ascending=False),
                use_container_width=True,
                column_config={
                    "Heure_Arrivee": st.column_config.TimeColumn("Heure d'arrivée", format="HH:mm"),
                    "Heure_Officielle": st.column_config.TimeColumn("Heure officielle", format="HH:mm"),
                    "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY")
                }
            )

            afficher_statistiques_retards(retards)
        else:
            st.info("Aucun retard enregistré")

    # --- SECTION STATISTIQUES ---
    elif menu == "Statistiques":
        st.header("Statistiques des Employés")

        employes = st.session_state.employes
        pointages = st.session_state.pointages
        retards = st.session_state.retards

        if not employes.empty:
            st.subheader("Répartition par service")
            service_counts = employes[employes["Actif"] == True]["Service"].value_counts()
            st.bar_chart(service_counts)

            if not pointages.empty:
                st.subheader("Heures travaillées")

                col1, col2 = st.columns(2)
                with col1:
                    selected_emp = st.selectbox(
                        "Sélectionner un employé",
                        employes[employes["Actif"] == True]["ID"].astype(str) + " - " +
                        employes[employes["Actif"] == True]["Prenom"] + " " +
                        employes[employes["Actif"] == True]["Nom"]
                    )
                    selected_id = int(selected_emp.split(" - ")[0])

                with col2:
                    date_range = st.date_input(
                        "Période",
                        [date.today() - timedelta(days=7), date.today()],
                        max_value=date.today()
                    )

                if len(date_range) == 2:
                    start_date, end_date = date_range
                    delta = timedelta(days=1)
                    dates = []
                    heures = []

                    current_date = start_date
                    while current_date <= end_date:
                        heures_trav = calculer_heures_travaillees(selected_id, current_date)
                        if heures_trav > timedelta(0):
                            dates.append(current_date)
                            heures.append(heures_trav.seconds / 3600)
                        current_date += delta

                    if dates:
                        df_heures = pd.DataFrame({"Date": dates, "Heures": heures})
                        st.line_chart(df_heures.set_index("Date"))

                        total_heures = sum(heures)
                        heures_semaine = total_heures / len(dates) * 5
                        st.metric("Total des heures", f"{total_heures:.1f}h")
                        st.metric("Moyenne journalière", f"{total_heures/len(dates):.1f}h/j")
                        st.metric("Projection hebdomadaire", f"{heures_semaine:.1f}h/sem")
                    else:
                        st.warning("Aucune donnée de pointage pour cette période")

    # --- SECTION ADMINISTRATION ---
    elif menu == "Administration":
        if st.session_state.get("role") != "admin":
            st.warning("Vous n'avez pas les permissions nécessaires pour accéder à cette section")
            return

        st.header("Configuration Admin")

        tab1, tab2 = st.tabs(["Gestion des Utilisateurs", "Configuration Système"])

        with tab1:
            st.subheader("Gestion des Utilisateurs")

            subtab1, subtab2, subtab3 = st.tabs(["Ajouter Utilisateur", "Modifier Utilisateur", "Supprimer Utilisateur"])

            with subtab1:
                with st.form("add_user_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        username = st.text_input("Nom d'utilisateur*")
                    with col2:
                        password = st.text_input("Mot de passe*", type="password")

                    col3, col4 = st.columns(2)
                    with col3:
                        nom = st.text_input("Nom*")
                    with col4:
                        prenom = st.text_input("Prénom*")

                    role = st.selectbox("Rôle*", ["admin", "manager", "user"])

                    if st.form_submit_button("Ajouter Utilisateur"):
                        if username and password and nom and prenom:
                            if ajouter_utilisateur(username, password, nom, prenom, role):
                                st.rerun()
                        else:
                            st.error("Veuillez remplir tous les champs obligatoires (*)")

            with subtab2:
                users = st.session_state.utilisateurs
                if users.empty:
                    st.warning("Aucun utilisateur à modifier")
                else:
                    search_term = st.text_input("Rechercher un utilisateur à modifier")
                    if search_term:
                        users_filtres = users[
                            users["Username"].str.contains(search_term, case=False) |
                            users["Nom"].str.contains(search_term, case=False) |
                            users["Prenom"].str.contains(search_term, case=False) |
                            users["Role"].str.contains(search_term, case=False)
                        ]
                    else:
                        users_filtres = users

                    if users_filtres.empty:
                        st.warning("Aucun utilisateur trouvé avec ce critère de recherche")
                    else:
                        selected = st.selectbox(
                            "Utilisateur à modifier",
                            users_filtres["ID"].astype(str) + " - " + users_filtres["Username"] + " (" + users_filtres["Role"] + ")"
                        )
                        selected_id = int(selected.split(" - ")[0])
                        user = users[users["ID"] == selected_id].iloc[0]

                        with st.form("modif_user_form"):
                            col1, col2 = st.columns(2)
                            with col1:
                                new_username = st.text_input("Nom d'utilisateur*", value=user["Username"])
                            with col2:
                                new_password = st.text_input("Nouveau mot de passe (laisser vide pour ne pas changer)", type="password")

                            col3, col4 = st.columns(2)
                            with col3:
                                new_nom = st.text_input("Nom*", value=user["Nom"])
                            with col4:
                                new_prenom = st.text_input("Prénom*", value=user["Prenom"])

                            new_role = st.selectbox("Rôle*", ["admin", "manager", "user"],
                                                    index=["admin", "manager", "user"].index(user["Role"]))

                            new_actif = st.checkbox("Actif", value=user["Actif"])

                            if st.form_submit_button("Modifier Utilisateur"):
                                modifier_utilisateur(selected_id, new_username, new_password or None,
                                                     new_nom, new_prenom, new_role, new_actif)
                                st.rerun()

            with subtab3:
                users = st.session_state.utilisateurs
                if users.empty or len(users) == 1:
                    st.warning("Aucun utilisateur supplémentaire à supprimer")
                else:
                    search_term = st.text_input("Rechercher un utilisateur à supprimer")
                    if search_term:
                        users_filtres = users[
                            (users["ID"] != 1) &
                            (
                                users["Username"].str.contains(search_term, case=False) |
                                users["Nom"].str.contains(search_term, case=False) |
                                users["Prenom"].str.contains(search_term, case=False) |
                                users["Role"].str.contains(search_term, case=False)
                            )
                        ]
                    else:
                        users_filtres = users[users["ID"] != 1]

                    if users_filtres.empty:
                        st.warning("Aucun utilisateur trouvé avec ce critère de recherche")
                    else:
                        to_delete = st.selectbox(
                            "Utilisateur à supprimer",
                            users_filtres["ID"].astype(str) + " - " +
                            users_filtres["Username"] + " (" + users_filtres["Role"] + ")"
                        )
                        selected_id = int(to_delete.split(" - ")[0])

                        if st.button("Supprimer définitivement", use_container_width=True, type="primary", key=f"suppr_user_{selected_id}"):
                            supprimer_utilisateur(selected_id)
                            st.success("Utilisateur supprimé avec succès!")
                            st.rerun()

            st.subheader("Liste des Utilisateurs")
            users = st.session_state.utilisateurs
            st.dataframe(users.drop(columns=["Password"]), use_container_width=True)

        with tab2:
            st.subheader("Configuration Système")

            col1, col2 = st.columns(2)
            with col1:
                new_heure_entree = st.time_input(
                    "Heure d'entrée par défaut",
                    value=st.session_state.HEURE_ENTREE_DEFAUT
                )
            with col2:
                new_heure_sortie = st.time_input(
                    "Heure de sortie par défaut",
                    value=st.session_state.HEURE_SORTIE_DEFAUT
                )

            new_seuil_retard = st.number_input(
                "Seuil de retard (minutes)",
                min_value=1,
                value=st.session_state.SEUIL_RETARD
            )

            if st.button("Enregistrer les paramètres", key="save_config"):
                st.session_state.HEURE_ENTREE_DEFAUT = new_heure_entree
                st.session_state.HEURE_SORTIE_DEFAUT = new_heure_sortie
                st.session_state.SEUIL_RETARD = new_seuil_retard
                save_data_to_csv()
                st.success("Paramètres enregistrés avec succès!")

            st.divider()

            st.subheader("Sauvegarde et restauration")

            # Export des données
            if st.button("Exporter toutes les données", key="export_all"):
                data = {
                    "utilisateurs": st.session_state.utilisateurs.to_dict(),
                    "employes": st.session_state.employes.to_dict(),
                    "pointages": st.session_state.pointages.to_dict(),
                    "retards": st.session_state.retards.to_dict(),
                    "absences": st.session_state.absences.to_dict(),
                    "config": {
                        "HEURE_ENTREE_DEFAUT": st.session_state.HEURE_ENTREE_DEFAUT.strftime("%H:%M"),
                        "HEURE_SORTIE_DEFAUT": st.session_state.HEURE_SORTIE_DEFAUT.strftime("%H:%M"),
                        "SEUIL_RETARD": st.session_state.SEUIL_RETARD
                    }
                }
                import json
                json_data = json.dumps(data, indent=4)
                st.download_button(
                    label="Télécharger la sauvegarde",
                    data=json_data,
                    file_name=f"pointage_sauvegarde_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

            # Import des données
            st.subheader("Restaurer des données")
            uploaded_file = st.file_uploader("Choisir un fichier de sauvegarde", type=["json"])

            if uploaded_file is not None:
                try:
                    import json
                    data = json.load(uploaded_file)

                    if st.button("Confirmer la restauration", key="restore_data"):
                        st.session_state.utilisateurs = pd.DataFrame(data["utilisateurs"])
                        st.session_state.employes = pd.DataFrame(data["employes"])
                        st.session_state.pointages = pd.DataFrame(data["pointages"])
                        st.session_state.retards = pd.DataFrame(data["retards"])
                        st.session_state.absences = pd.DataFrame(data["absences"])

                        config = data["config"]
                        st.session_state.HEURE_ENTREE_DEFAUT = datetime.strptime(config["HEURE_ENTREE_DEFAUT"], "%H:%M").time()
                        st.session_state.HEURE_SORTIE_DEFAUT = datetime.strptime(config["HEURE_SORTIE_DEFAUT"], "%H:%M").time()
                        st.session_state.SEUIL_RETARD = config["SEUIL_RETARD"]

                        save_data_to_csv()
                        st.success("Données restaurées avec succès!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de la lecture du fichier: {str(e)}")

    # Bouton de déconnexion toujours visible
    if st.sidebar.button("Se déconnecter", use_container_width=True, key="logout_btn"):
        st.session_state["authenticated"] = False
        st.rerun()

if __name__ == "__main__":
    # Initialiser les données
    if not st.session_state.get('initialized', False):
        load_data_from_csv()
        st.session_state.initialized = True
    
    if not st.session_state.get("authenticated", False):
        login_page()
    else:
        main_app()