import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
import os
import csv
import hashlib

# Configuration de la page
st.set_page_config(
    page_title="Application de Pointage", 
    layout="wide",
    initial_sidebar_state="auto"
)

# Chemins des fichiers
EMPLOYES_FILE = "employes.csv"
POINTAGE_FILE = "pointage.csv"
RETARDS_FILE = "retards.csv"
UTILISATEURS_FILE = "utilisateurs.csv"

# Heures par défaut
HEURE_ENTREE_DEFAUT = time(8, 0)  # 8h00
HEURE_SORTIE_DEFAUT = time(17, 0)  # 17h00
SEUIL_RETARD = 15  # minutes

# Services disponibles
SERVICES_DISPONIBLES = [
    "Administration",
    "Production",
    "Comptabilité",
    "Ressources Humaines",
    "Informatique",
    "Commercial"
]

# Fonction de hachage pour les mots de passe
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Créer les fichiers s'ils n'existent pas
def init_files():
    # Fichier des employés
    if not os.path.exists(EMPLOYES_FILE):
        with open(EMPLOYES_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Nom", "Prenom", "Service", "Heure_Entree", "Heure_Sortie"])
    
    # Fichier de pointage
    if not os.path.exists(POINTAGE_FILE):
        with open(POINTAGE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Nom", "Prenom", "Service", "Type", "Heure", "Date"])
    
    # Fichier des retards
    if not os.path.exists(RETARDS_FILE):
        with open(RETARDS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Nom", "Prenom", "Service", "Heure_Arrivee", "Heure_Officielle", "Retard_min", "Retard_affichage", "Date"])
    
    # Fichier des utilisateurs (pour l'authentification)
    if not os.path.exists(UTILISATEURS_FILE):
        with open(UTILISATEURS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Username", "Password", "Role"])
            # Ajouter un admin par défaut
            writer.writerow(["admin", hash_password("admin"), "admin"])

# Charger les données
def load_data(filename):
    try:
        return pd.read_csv(filename)
    except:
        return pd.DataFrame()

# Sauvegarder les données
def save_data(df, filename):
    df.to_csv(filename, index=False, encoding='utf-8')

# Convertir string en time
def str_to_time(time_str):
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except:
        return HEURE_ENTREE_DEFAUT

# Fonction d'authentification
def authenticate(username, password):
    users = load_data(UTILISATEURS_FILE)
    if not users.empty:
        user = users[users["Username"] == username]
        if not user.empty and user.iloc[0]["Password"] == hash_password(password):
            return user.iloc[0]["Role"]
    return None

# Fonction pour créer un nouvel utilisateur
def create_user(username, password, role):
    users = load_data(UTILISATEURS_FILE)
    if username in users["Username"].values:
        return False
    new_user = pd.DataFrame([[username, hash_password(password), role]], 
                          columns=["Username", "Password", "Role"])
    users = pd.concat([users, new_user], ignore_index=True)
    save_data(users, UTILISATEURS_FILE)
    return True

# Fonctions de gestion du personnel
def ajouter_employe(nom, prenom, service, heure_entree=None, heure_sortie=None):
    df = load_data(EMPLOYES_FILE)
    new_id = df["ID"].max() + 1 if not df.empty else 1
    
    if heure_entree is None:
        heure_entree = HEURE_ENTREE_DEFAUT
    if heure_sortie is None:
        heure_sortie = HEURE_SORTIE_DEFAUT
    
    new_employe = pd.DataFrame([[new_id, nom, prenom, service, heure_entree.strftime("%H:%M"), heure_sortie.strftime("%H:%M")]], 
                            columns=["ID", "Nom", "Prenom", "Service", "Heure_Entree", "Heure_Sortie"])
    df = pd.concat([df, new_employe], ignore_index=True)
    save_data(df, EMPLOYES_FILE)
    st.success(f"Employé {prenom} {nom} ajouté avec succès!")

def modifier_employe(id_employe, nom=None, prenom=None, service=None, heure_entree=None, heure_sortie=None):
    df = load_data(EMPLOYES_FILE)
    idx = df[df["ID"] == id_employe].index[0]
    
    if nom: df.at[idx, "Nom"] = nom
    if prenom: df.at[idx, "Prenom"] = prenom
    if service: df.at[idx, "Service"] = service
    if heure_entree: 
        heure_entree = heure_entree.time() if isinstance(heure_entree, datetime) else heure_entree
        df.at[idx, "Heure_Entree"] = heure_entree.strftime("%H:%M")
    if heure_sortie: 
        heure_sortie = heure_sortie.time() if isinstance(heure_sortie, datetime) else heure_sortie
        df.at[idx, "Heure_Sortie"] = heure_sortie.strftime("%H:%M")
    
    save_data(df, EMPLOYES_FILE)
    st.success("Employé modifié avec succès!")

def supprimer_employe(id_employe):
    df = load_data(EMPLOYES_FILE)
    df = df[df["ID"] != id_employe]
    save_data(df, EMPLOYES_FILE)
    st.success("Employé supprimé avec succès!")

# Fonctions de pointage améliorées
def pointer(id_employe, type_pointage):
    employes = load_data(EMPLOYES_FILE)
    employe = employes[employes["ID"] == id_employe].iloc[0]
    
    now = datetime.now()
    heure_actuelle = now.time()
    date_actuelle = now.date()
    
    # Vérifier si l'employé a déjà pointé ce type aujourd'hui
    pointages = load_data(POINTAGE_FILE)
    today_pointages = pointages[(pointages["ID"] == id_employe) & 
                               (pointages["Date"] == date_actuelle.strftime("%Y-%m-%d")) &
                               (pointages["Type"] == type_pointage)]
    
    if not today_pointages.empty:
        st.warning(f"Vous avez déjà enregistré une {type_pointage.lower()} aujourd'hui à {today_pointages.iloc[0]['Heure']}")
        return
    
    # Enregistrement du pointage
    new_pointage = pd.DataFrame([[id_employe, employe["Nom"], employe["Prenom"], employe["Service"], 
                                type_pointage, heure_actuelle.strftime("%H:%M"), date_actuelle.strftime("%Y-%m-%d")]],
                              columns=["ID", "Nom", "Prenom", "Service", "Type", "Heure", "Date"])
    pointages = pd.concat([pointages, new_pointage], ignore_index=True)
    save_data(pointages, POINTAGE_FILE)
    st.success(f"{type_pointage} enregistrée à {heure_actuelle.strftime('%H:%M')}")
    
    # Vérification des retards pour l'arrivée
    if type_pointage == "Entrée":
        heure_officielle = str_to_time(employe["Heure_Entree"])
        retard_min = (datetime.combine(date_actuelle, heure_actuelle) - 
                    datetime.combine(date_actuelle, heure_officielle)).total_seconds() / 60
        
        if retard_min > SEUIL_RETARD:
            # Convertir les minutes en heures et minutes
            heures = int(retard_min // 60)
            minutes = int(retard_min % 60)
            retard_str = f"{heures}h{minutes:02d}m" if heures > 0 else f"{minutes}m"
            
            df_retards = load_data(RETARDS_FILE)
            new_retard = pd.DataFrame([[id_employe, employe["Nom"], employe["Prenom"], employe["Service"], 
                                      heure_actuelle.strftime("%H:%M"), heure_officielle.strftime("%H:%M"), 
                                      round(retard_min), retard_str, date_actuelle.strftime("%Y-%m-%d")]],
                                    columns=["ID", "Nom", "Prenom", "Service", "Heure_Arrivee", 
                                           "Heure_Officielle", "Retard_min", "Retard_affichage", "Date"])
            df_retards = pd.concat([df_retards, new_retard], ignore_index=True)
            save_data(df_retards, RETARDS_FILE)
            st.warning(f"Retard enregistré: {retard_str}")

# Calculer les heures travaillées amélioré
def calculer_heures_travaillees(id_employe, date):
    pointages = load_data(POINTAGE_FILE)
    pointages_date = pointages[(pointages["ID"] == id_employe) & 
                             (pointages["Date"] == date.strftime("%Y-%m-%d"))]
    
    entrees = pointages_date[pointages_date["Type"] == "Entrée"]["Heure"].sort_values()
    sorties = pointages_date[pointages_date["Type"] == "Sortie"]["Heure"].sort_values()
    
    if len(entrees) == 0 or len(sorties) == 0:
        return timedelta(0)
    
    # Calculer le temps total entre la première entrée et la dernière sortie
    premiere_entree = str_to_time(entrees.iloc[0])
    derniere_sortie = str_to_time(sorties.iloc[-1])
    
    # Calculer les pauses entre les sorties et entrées suivantes
    temps_travaille = datetime.combine(date, derniere_sortie) - datetime.combine(date, premiere_entree)
    
    # Si plusieurs entrées/sorties, soustraire les pauses
    if len(entrees) > 1 and len(sorties) > 1:
        for i in range(1, min(len(entrees), len(sorties))):
            sortie = str_to_time(sorties.iloc[i-1])
            entree = str_to_time(entrees.iloc[i])
            pause = datetime.combine(date, entree) - datetime.combine(date, sortie)
            temps_travaille -= pause
    
    return temps_travaille

# Page de connexion
def login_page():
    st.title("Connexion à l'application de pointage")
    
    with st.form("login_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")
        
        if submit:
            role = authenticate(username, password)
            if role:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["role"] = role
                st.rerun()
            else:
                st.error("Nom d'utilisateur ou mot de passe incorrect")

# Page d'administration des utilisateurs
def admin_users_page():
    st.header("Gestion des utilisateurs")
    
    with st.expander("Ajouter un nouvel utilisateur"):
        with st.form("add_user_form"):
            new_username = st.text_input("Nom d'utilisateur")
            new_password = st.text_input("Mot de passe", type="password")
            new_role = st.selectbox("Rôle", ["admin", "manager", "user"])
            submit = st.form_submit_button("Ajouter l'utilisateur")
            
            if submit:
                if create_user(new_username, new_password, new_role):
                    st.success("Utilisateur créé avec succès")
                else:
                    st.error("Ce nom d'utilisateur existe déjà")
    
    st.subheader("Liste des utilisateurs")
    users = load_data(UTILISATEURS_FILE)
    if not users.empty:
        # Ne pas afficher les mots de passe
        display_users = users.copy()
        display_users["Password"] = "********"
        st.dataframe(display_users)
    else:
        st.info("Aucun utilisateur enregistré")

# Page de pointage améliorée
def pointage_page():
    st.header("Enregistrement des pointages")
    
    employes = load_data(EMPLOYES_FILE)
    if employes.empty:
        st.warning("Aucun employé enregistré. Veuillez ajouter des employés d'abord.")
        return
    
    # Section de recherche améliorée
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔍 Rechercher un employé par nom ou prénom")
    with col2:
        filter_service = st.selectbox("Filtrer par service", ["Tous"] + SERVICES_DISPONIBLES)
    
    if search_term:
        employes = employes[employes["Nom"].str.contains(search_term, case=False) | 
                         employes["Prenom"].str.contains(search_term, case=False)]
    
    if filter_service != "Tous":
        employes = employes[employes["Service"] == filter_service]
    
    if employes.empty:
        st.warning("Aucun employé trouvé avec ces critères")
        return
    
    # Sélection d'employé avec plus d'informations
    selected_emp = st.selectbox(
        "Sélectionnez un employé", 
        employes.apply(lambda x: f"{x['ID']} - {x['Prenom']} {x['Nom']} ({x['Service']})", axis=1)
    )
    selected_id = int(selected_emp.split(" - ")[0])
    employe = employes[employes["ID"] == selected_id].iloc[0]
    
    # Affichage des informations de l'employé
    st.info(f"""
    **Service:** {employe['Service']}  
    **Heure d'entrée officielle:** {employe['Heure_Entree']}  
    **Heure de sortie officielle:** {employe['Heure_Sortie']}
    """)
    
    # Boutons de pointage avec confirmation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🟢 Enregistrer l'arrivée", help="Cliquez pour enregistrer l'heure d'arrivée", use_container_width=True):
            pointer(selected_id, "Entrée")
    with col2:
        if st.button("🔴 Enregistrer la sortie", help="Cliquez pour enregistrer l'heure de sortie", use_container_width=True):
            pointer(selected_id, "Sortie")
    
    # Section des pointages récents
    st.subheader("Historique récent")
    pointages = load_data(POINTAGE_FILE)
    if not pointages.empty:
        recent_pointages = pointages[pointages["ID"] == selected_id].sort_values(by=["Date", "Heure"], ascending=False).head(5)
        if not recent_pointages.empty:
            st.dataframe(recent_pointages[["Type", "Heure", "Date"]], hide_index=True)
        else:
            st.info("Aucun pointage enregistré pour cet employé")
    
    # Calcul des heures travaillées aujourd'hui
    today = datetime.now().date()
    heures_travaillees = calculer_heures_travaillees(selected_id, today)
    heures = heures_travaillees.seconds // 3600
    minutes = (heures_travaillees.seconds // 60) % 60
    st.metric("Heures travaillées aujourd'hui", f"{heures}h{minutes:02d}m")

# Interface principale
def main_app():
    init_files()
    
    st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    """, unsafe_allow_html=True)
    
    # Menu adaptatif en fonction du rôle
    if st.session_state.get("role") == "admin":
        menu_options = ["Pointage", "Gestion du Personnel", "Historique", "Retards", "Statistiques", "Administration"]
    elif st.session_state.get("role") == "manager":
        menu_options = ["Pointage", "Gestion du Personnel", "Historique", "Retards", "Statistiques"]
    else:
        menu_options = ["Pointage", "Historique"]
    
    if st.sidebar.button("Déconnexion"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.sidebar.title(f"Menu ({st.session_state.get('role', 'user')})")
    menu = st.sidebar.selectbox("Navigation", menu_options)
    
    if menu == "Pointage":
        pointage_page()
    elif menu == "Gestion du Personnel" and st.session_state.get("role") in ["admin", "manager"]:
        gestion_personnel_page()
    elif menu == "Historique":
        historique_page()
    elif menu == "Retards" and st.session_state.get("role") in ["admin", "manager"]:
        retards_page()
    elif menu == "Statistiques" and st.session_state.get("role") in ["admin", "manager"]:
        statistiques_page()
    elif menu == "Administration" and st.session_state.get("role") == "admin":
        admin_users_page()

# Pages supplémentaires (à implémenter de manière similaire)
def gestion_personnel_page():
    st.header("Gestion du Personnel")
    # ... (le code existant pour la gestion du personnel)

def historique_page():
    st.header("Historique des Pointages")
    # ... (le code existant pour l'historique)

def retards_page():
    st.header("Historique des Retards")
    # ... (le code existant pour les retards)

def statistiques_page():
    st.header("Statistiques des Employés")
    # ... (le code existant pour les statistiques)

# Point d'entrée de l'application
if __name__ == "__main__":
    if not st.session_state.get("authenticated"):
        login_page()
    else:
        main_app()