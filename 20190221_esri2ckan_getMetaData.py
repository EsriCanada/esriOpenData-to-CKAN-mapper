# -*- coding: UTF-8 -*-

'''
Script développé par Jonathan Gaudreau, pour Esri Canada, 2017
Ce script permet de mapper les champs de métadonnées d'une page ArcGIS Online Open Data vers
les métadonnées de l'instance CKAN de Données Québec.
Il doit être intégré à un fichier .BAT et une tâche planifiée.
'''

#Importation des librairies utilisées
import json
from pprint import pprint
import csv
import os, sys
import requests, datetime, time
from xml.etree import ElementTree
from datetime import datetime
from html2text import html2text
from colorama import Fore, Back, Style

# ##### ##### ##### ##### ##### ##### ##### #
#
# Définition des Variables locales et globales
#
# ##### ##### ##### ##### ##### ##### ##### #


#Identification des fichiers repères
fichierListeCategories      = "categories.csv"
fichierListeCategoriesPlus  = "categoriesplus.csv"
fichierListeOrganisations   = "organisations.csv"
fichierModeleESRI2CKAN      = "esri2ckan.json"

#Identification des fichiers et dossiers repères pour les logs
dossierLogIntitule          = "logesri2ckan"
fichierLogPrefixe           = "esri2ckan"
fichierLogExtension         = ".log"


#Adresse du Serveur Web de publication
URLServeurActuel            = "https://www.donneesquebec.ca"

#définition du mode Humeur. True > les mesages d'erreur et de notification sont affichés, False > mode silencieux
#lorsque modeHumeur = False, seuls les messages d'erreur ou les message des section except seront affichés éventuellement
modeHumeur  = True

#Identification du répertoire dans lequel le script se trouve et identification du template CKAN
repertoire  = os.getcwd()
found       = False
tableliee   = os.path.join(repertoire, fichierListeOrganisations)

#Définition du séparateur utilisé pour le rendu dans le terminal
separateur  = "----- "

#Détection du système d'exploitation
if os.name == 'nt':
    #Formalisme Windows
    SlashDossier = "\\"
else:
    #Formalisme Linux
    SlashDossier = "/"

# ##### ##### ##### ##### ##### ##### ##### #
#
# Définition des Procédures et Fonctions
#
# ##### ##### ##### ##### ##### ##### ##### #

#afficheHumeur : fonction n'affichant des messages donnés que si le mode Humeur est activé
def afficheHumeur (descriptionHumeur) :
    global modeHumeur
    global modeLog
    global logActuel
    if (modeHumeur == True) :
        print (descriptionHumeur)
    if (modeLog == True) :
        logActuel.write("\n" + descriptionHumeur)


#afficheErreur : fonction affichant les messages d'erreur de manière fort notable/remarquable
#   note : les messages d'erreurs sont toujours affichés, même si le modeHumeur est faux
def afficheErreur (intituleErreur) :
    global modeLog
    global logActuel
    #on affiche le message d'erreur en Blanc sur fond Rouge, puis on revient à la normale juste après
    print (Back.RED + Fore.WHITE + intituleErreur)
    print (Style.RESET_ALL)
    if (modeLog == True) :
        logActuel.write("\n" + intituleErreur)

#getMetadata : fonction recueillant les métadonnées du jeu spécifié en paramètre
def getMetadata(itemID):
    r = requests.get("https://www.arcgis.com/sharing/rest/content/items/"+itemID+"/info/metadata/metadata.xml?format=default")
    print("itemID: " + str(itemID) + " ")
    print("code: " + str(r.status_code))
    tree = ElementTree.fromstring(r.content)
    taggs = []
    tagsXML = tree.findall('idinfo')[0].findall('keywords')[0].findall('theme')[0].findall('themekey')
    print("Liste de tags: ")
    for item in tagsXML:
        print("\t" + item.text)
        taggs.append(item.text)
    try:    
        abstract = tree.findall('idinfo')[0].findall('descript')[0].findall('abstract')[0].text
    except:
        print("ERREUR AVEC ABSTRACT!!")
        abstract = ""
    print("Abstract: " + abstract)
    try:
        supplinf = tree.findall('idinfo')[0].findall('descript')[0].findall('supplinf')[0].text
    except:
        afficheErreur (separateur * 3 + "ERREUR : Erreur avec les informations supplémentaires. Cause probable : " + str(e))
        supplinf = ""
    print("supplinf: " + supplinf)

    # gestion de la fréquence de mise à jour
    try:
        freqUpdate = tree.findall('idinfo')[0].findall('status')[0].findall('update')[0].text
    except Exception as e:
        afficheErreur (separateur * 3 + "ERREUR : Récupération de la Fréquence de mise à jour impossible. Cause probable : " + str(e))
        freqUpdate = "asNeeded"
    if freqUpdate == "As needed":
        freqUpdate = "asNeeded"
    elif freqUpdate == "Not planned":
        freqUpdate = "notPlanned"
    else:
        freqUpdate = freqUpdate.lower()
    afficheHumeur ("Freq update: " + freqUpdate)

    return abstract, supplinf, taggs, freqUpdate
    

#moissonneClientESRI : fonction effectuant le processus entier de moissonnage pour le clientESRI spécifié
def moissonneClientESRI (clientESRI) :
    afficheHumeur ("\nProcessus de moissonnage exécuté pour : [" + clientESRI + "]")

    found = False

    with open(tableliee, "r") as tableCSV:
        cols    = tableCSV.readline()
        donnees = tableCSV.read().split("\n")

    for i in range(0,len(donnees)):
        if donnees[i].split(",")[0] == clientESRI:
            afficheHumeur (separateur * 1 + "Correspondance trouvée.")
            ownerOrg    = donnees[i].split(",")[1]
            extSpatial  = donnees[i].split(",")[2]
            arcgisUrl   = donnees[i].split(",")[3]
            found       = True
            break

    if found == True:
        outFolder = os.path.join(repertoire,"outputs" + SlashDossier + ownerOrg)
        try:
            if not (os.path.exists(outFolder)):
                os.makedirs(outFolder)
        except OSError as e:
            afficheErreur (separateur * 3 + "ERREUR : Création du dossier de sortie impossible. Cause probable : " + str(e))
            pass

        modele          = os.path.join(repertoire, fichierModeleESRI2CKAN)
        timestart       = datetime.now()

        #Chargement de l'URL Open Data
        url             = arcgisUrl
        response        = requests.get(url)
        source          = response.json()

        #Affichage du nombre de jeux de données répertoriés par data.json
        nbLayers        = len(source['dataset'])
        listeCouches    = ""
        listeFormats    = []

        #Création d'une liste d'ID uniques
        newIDs          = []
        newtimeStamps   = []
        newTags         = []
        afficheHumeur (separateur * 1 + str(nbLayers) + " couches présentes sur OpenData.")
        afficheHumeur (separateur * 1 + "Début du traitement")

        #Boucle qui parcourt les datasets les uns après les autres.
        for i in range(0, nbLayers):
            categorie   = ""
            with open(modele) as data_file:
                target  = json.load(data_file)
            listeFormats=[]

            #Identification des formats des datasets
            for k in range(0,len(source['dataset'][i]['distribution'])):
                listeFormats.append(source['dataset'][i]['distribution'][k]['format'])

            #Récupération de l'ID unique et des champs communs à la ressource.
            uniqueID = source['dataset'][i]['identifier'].split("/")[len(source['dataset'][i]['identifier'].split("/"))-1]
            newIDs.append(uniqueID)
            newtimeStamps.append(source['dataset'][i]['modified'])
            target['title']         = source['dataset'][i]['title']
            description             = source['dataset'][i]['description']
            target['description']   = html2text(description)
            target['notes']         = html2text(description)
            target['name']          = uniqueID
            title                   = target['title']

            #Récupération des valeurs des champs additionnels
            try:
                abstract, supplinf, taggs, freqUpdate = getMetadata(uniqueID[:-2])

            #afficheHumeur (separateur * 3 + u"---- ---- ---- description : " + description)

            #Construction de la liste des mots-clés dans une seule séquence
            #Par la suite, on écrit la liste, sans le dernier caractère, pour enlever la virgule finale (inutile)

                target['num_tags'] = len(taggs)
                for j in range(0, min(len(taggs),40)):
                        target['tags'][j]['display_name'] = taggs[j]
                        target['tags'][j]['name'] = taggs[j]
                        try:
                            tagIndex    = categories.index(taggs[j].lower())
                            categorie  += '"' + categories[tagIndex] + '",'
                        except ValueError as e:
                            afficheErreur (separateur * 3 + "ERREUR : Construction de la liste des mots-clés perturbée. Cause probable : " + str(e))
                            pass
                target['update_frequency']                  = freqUpdate

            except:
                supplinf = ""
                categories2 = []
                for categoritem in categories:
                    categories2.append(categoritem.replace("-",""))
                target['num_tags'] = len(source['dataset'][i]['keyword'])
                for j in range(0, min(len(source['dataset'][i]['keyword']),40)):
                        target['tags'][j]['display_name'] = source['dataset'][i]['keyword'][j]
                        target['tags'][j]['name'] = source['dataset'][i]['keyword'][j]
                        try:
                            tagIndex    = categories2.index(source['dataset'][i]['keyword'][j])
                            if categories2[tagIndex] == "agriculturealimentation":
                                categories2[tagIndex]="agriculture-alimentation"
                                target['tags'][j]['name'] = ""
                            elif categories2[tagIndex] == "economieentreprises":
                                categories2[tagIndex]="economie-entreprises"
                                target['tags'][j]['name'] = ""
                            elif categories2[tagIndex] == "educationrecherche":
                                categories2[tagIndex]="education-recherche"
                                target['tags'][j]['name'] = ""
                            elif categories2[tagIndex] == "environnementressourcesnaturellesenergie":
                                categories2[tagIndex]="environnement-ressources-naturelles-energie"
                                target['tags'][j]['name'] = ""
                            elif categories2[tagIndex] == "gouvernementfinances":
                                categories2[tagIndex]="gouvernement-finances"
                                target['tags'][j]['name'] = ""
                            elif categories2[tagIndex] == "loijusticesecuritepublique":
                                categories2[tagIndex]="loi-justice-securite-publique"
                                target['tags'][j]['name'] = ""
                            elif categories2[tagIndex] == "politiquessociales":
                                categories2[tagIndex]="politiques-sociales"
                                target['tags'][j]['name'] = ""
                            elif categories2[tagIndex] == "societeculture":
                                categories2[tagIndex]="societe-culture"
                                target['tags'][j]['name'] = ""
                            elif categories2[tagIndex] == "tourismesportsloisirs":
                                categories2[tagIndex]="tourisme-sports-loisirs"
                                target['tags'][j]['name'] = ""
                            elif categories2[tagIndex] == "sante":
                                categories2[tagIndex]="sante"
                                target['tags'][j]['name'] = ""
                            elif categories2[tagIndex] == "transport":
                                categories2[tagIndex]="transport"
                                target['tags'][j]['name'] = ""
                            elif categories2[tagIndex] == "infrastructures":
                                categories2[tagIndex]="infrastructures"
                                target['tags'][j]['name'] = ""
                            categorie  += '"' + categories2[tagIndex] + '",'
                        except ValueError:
                            pass
            target['methodologie']  = html2text(supplinf)


            #print(categorie)

            newTags.append("[" + categorie[:-1]+"]")

            if categorie != "":
                nombreCategories = len(categorie[:-1].split(","))
            else :
                nombreCategories = 0


            if (nombreCategories > 0) :
                for nbcat in range (0, nombreCategories) :
                    categorie_actuelle = categorie[:-1].split(",")[nbcat].replace('"', '')
                    for indexCat in range(0,len(contenuCSV)):
                        if groups_name[indexCat].lower() == categorie_actuelle.lower():
                            target['groups'][nbcat]['display_name']         = groups_display_name[indexCat]
                            target['groups'][nbcat]['description']          = groups_description[indexCat]
                            target['groups'][nbcat]['image_display_url']    = groups_image_display_url[indexCat]
                            target['groups'][nbcat]['title']                = groups_title[indexCat]
                            target['groups'][nbcat]['id']                   = groups_id[indexCat]
                            target['groups'][nbcat]['name']                 = categorie_actuelle

            #Création du morceau JSON qui ira dans le Package_list.json (index)
            listeCouches += '{"ID": ' + '"' + uniqueID + '","timestamp" : ' + '"' + source['dataset'][i]['modified'] +  '","categorie" : ' + "[" + categorie[:-1] + "]" + '},'

            #logique de validation qui supprimera les TAGS laissés vides.
            correct = False
            while correct != True:
                if target['tags'][len(target['tags'])-1]['name']== "":
                        target['tags'].remove(target['tags'][len(target['tags'])-1])
                else:
                    correct = True
            target['author']                            = source['dataset'][i]['contactPoint']['fn']
            target['extras_organisation_principale']    = clientESRI
            target['owner_org']                         = ownerOrg
            target["ext_spatial"]                       = extSpatial
            target['author_email']                      = source['dataset'][i]['contactPoint']['hasEmail'][7:]
            target['url']                               = source['dataset'][i]['identifier']
            target['metadata_created']                  = source['dataset'][i]['issued']
            target['metadata_modified']                 = source['dataset'][i]['modified'].replace(".000Z","")
            #target['update_frequency']                  = freqUpdate

            #FORMAT WEB PAGE
            try:
                indexPage = listeFormats.index("Web page")
                target['resources'][0]['url']           = source['dataset'][i]['distribution'][indexPage]['accessURL']
                target['resources'][0]['name']          = title + " - HTML"
                target['resources'][0]['resource_type'] = "cartes"
                afficheHumeur ("---- ---- " + title)
                afficheHumeur ("---- ---- ---- catégories : " + (categorie[:-1] or "(vide)"))
            except:
                afficheErreur (separateur * 3 + "Web Page format introuvable")

            #FORMAT REST
            try:
                indexREST = listeFormats.index("Esri REST")
                target['resources'][1]['url']           = source['dataset'][i]['distribution'][indexREST]['accessURL']
                target['resources'][1]['name']          = title + " - Service REST"
                target['resources'][1]['resource_type'] = "web"
            except:
                afficheErreur (separateur * 3 + "REST format introuvable")

            #FORMAT GEOJSON
            try:
                indexGeoJSON = listeFormats.index("GeoJSON")
                target['resources'][2]['url']           = source['dataset'][i]['distribution'][indexGeoJSON]['downloadURL']
                target['resources'][2]['name']          = title + " - GeoJSON"
                target['resources'][2]['resource_type'] = "donnees"
            except:
                afficheErreur (separateur * 3 + "GeoJSON format introuvable")

            #FORMAT CSV
            try:
                indexCSV  = listeFormats.index("CSV")
                target['resources'][3]['url']           = source['dataset'][i]['distribution'][indexCSV]['downloadURL']
                target['resources'][3]['name']          = title + " - CSV"
                target['resources'][3]['resource_type'] = "donnees"
            except:
                afficheErreur (separateur * 3 + "CSV format introuvable")

            #FORMAT KML
            try:
                indexKML  = listeFormats.index("KML")
                target['resources'][4]['url']           = source['dataset'][i]['distribution'][indexKML]['downloadURL']
                target['resources'][4]['name']          = title + " - KML"
                target['resources'][4]['resource_type'] = "donnees"
            except:
                afficheErreur (separateur * 3 + "KML format introuvable")

            #FORMAT SHP (ZIP)
            try:
                indexSHP  = listeFormats.index("ZIP")
                target['resources'][5]['url']           = source['dataset'][i]['distribution'][indexSHP]['downloadURL']
                target['resources'][5]['name']          = title + " - ZIP"
                target['resources'][5]['resource_type'] = "donnees"
            except:
                afficheErreur (separateur * 3 + "SHP format introuvable")

            #Écriture du fichier traité
            with open(outFolder + SlashDossier + uniqueID + u".json", 'w') as sortie:
                json.dump(target, sortie)
        afficheHumeur (separateur * 1 + "Fin de l'écriture du CSV initial")
        afficheHumeur ("\n")

        #Écriture de l'index
        if not os.path.exists(outFolder + SlashDossier + "package_list.json"):
            afficheHumeur (separateur * 1 + "L'index n'existe pas. Création de l'index initial")
            listeCouches = listeCouches[:-1]
            with open(outFolder + SlashDossier + "package_list.json",'w') as index:
                index.write('{"help": "https://www.donneesquebec.ca/recherche/api/3/action/help_show?name=package_list", "success": true, "result": ['+listeCouches+']}')
        else:
            #Si l'index existe, mise à jour de l'index et changement de la valeur d'état.
            afficheHumeur (separateur * 1 + "L'index existe. Mise à jour de l'index.")

            try:
                url = URLServeurActuel + "/recherche/api/3/action/package_search?q=organization:" + clientESRI + "&rows=100000"
                print(url)
                response = requests.get(url)
            except:
                afficheErreur (separateur * 1 + "ERREUR : L'instance CKAN ne contient pas de données pour l'organisation " + clientESRI)
                time.sleep(3)
                sys.exit()
            ckanData    = response.json()
            ckanRes     = ckanData['result']['results']
            nbLayers    = len(ckanRes)
            afficheHumeur (separateur * 2 + str(nbLayers) + " couches sur CKAN")

            oldIDs          = []
            oldtimestamps   = []

            for i in range(0, nbLayers):
                if ckanRes[i]['name'].find("_")!= -1:
                    oldIDs.append(ckanRes[i]['name'])
                    oldtimestamps.append(ckanRes[i]['metadata_modified'].replace(".000Z",""))


            outIDs          = []
            outtimestamps   = []
            outStates       = []
            outCategories   = []

            #Identification des ajouts
            for i in range(0, len(newIDs)):
                if newIDs[i] in oldIDs:
                    pass
                else:
                    outIDs.append(newIDs[i])
                    outtimestamps.append(newtimeStamps[i])
                    outStates.append("AJOUT")
                    outCategories.append(newTags[i])

            #Identification des suppressions
            for i in range(0, len(oldIDs)):
                if oldIDs[i] in newIDs:
                    pass
                else:
                    outIDs.append(oldIDs[i])
                    outtimestamps.append(oldtimestamps[i])
                    outStates.append("SUPPRESSION")
                    outCategories.append("[]")

            #Identifications des plus récents (mis à jour)
            for i in range(0, len(newIDs)):
                if newIDs[i] in oldIDs:
                    outIDs.append(newIDs[i])
                    outtimestamps.append(newtimeStamps[i])
                    indexGood = oldIDs.index(newIDs[i])
                    newDate = datetime.strptime(newtimeStamps[i],"%Y-%m-%dT%H:%M:%S.%fZ")
                    try:
                        oldDate = datetime.strptime(oldtimestamps[indexGood],"%Y-%m-%dT%H:%M:%S")
                    except:
                        oldDate = datetime.strptime(oldtimestamps[indexGood],"%Y-%m-%dT%H:%M:%S.%f")

                    if newtimeStamps[i] > oldtimestamps[indexGood]:
                        outStates.append("MODIFICATION")
                    else:
                        outStates.append("AUCUN CHANGEMENT")

                    outCategories.append(newTags[i])
                    #afficheHumeur (separateur * 3 + "NewTags")
                    #afficheHumeur (separateur * 3 + str(i) + " " + newTags[i])

            listeCouches = ""
            #Création du morceau de JSON pour Package_list.json, l'index.
            for i in range(0, len(outIDs)):
                listeCouches += '{"ID": ' + '"' + str(outIDs[i]) + '","timestamp" : ' + '"' + str(outtimestamps[i]) +'","etat" : "' + str(outStates[i]) +  '","categorie" : ' + outCategories[i]  + '},'
            listeCouches = listeCouches[:-1]
            with open(outFolder + SlashDossier + "package_list.json", "w") as index:
                index.write('{"help": "https://www.donneesquebec.ca/recherche/api/3/action/help_show?name=package_list", "success": true, "result": ['+listeCouches+']}')
        timeEnd = datetime.now()-timestart

        afficheHumeur (separateur * 1 + "Traitement effectué en " + str(timeEnd.total_seconds()) + " secondes")
        afficheHumeur ("Fin du Processus de moissonnage de : [" + clientESRI + "]")
    else:
        afficheErreur (separateur * 1 + "ERREUR : Erreur de traitement. La ville entrée en paramètre [" + clientESRI + "] n'existe pas dans le système, ou est mal écrite (sensibilité à la casse). Bien vouloir vérifier.")

# ##### ##### ##### ##### ##### ##### ##### #
#
# Programme "normal"
#
# ##### ##### ##### ##### ##### ##### ##### #


#Récupération des catégories
with open(os.path.join(repertoire, fichierListeCategories),"r") as cats:
    categories = cats.readline().split(",")
#print(categories)

#Récupération des Catégories Plus (complètes/élaborées)
with open(os.path.join(repertoire, fichierListeCategoriesPlus),"r") as categoriespleines:
    #on utilise le ; comme délimiteur dans le CSV avant de ne pas courcircuiter les catégories comportant des virgules en leur sein
    lecteurCSV = csv.reader(categoriespleines, delimiter = ';')
    next(lecteurCSV) # on saute l'en-tête
    contenuCSV = [ligneCSV for ligneCSV in lecteurCSV]

#initialisation de notre matrice de caractéristiques des catégories/groupes
groups_display_name         = []
groups_description          = []
groups_image_display_url    = []
groups_title                = []
groups_id                   = []
groups_name                 = []

#conservation en mémoire des cellules de notre tableau/matrice de catégories
for i in range(0,len(contenuCSV)):
    groups_display_name.append(contenuCSV[i][0])
    groups_description.append(contenuCSV[i][1])
    groups_image_display_url.append(contenuCSV[i][2])
    groups_title.append(contenuCSV[i][3])
    groups_id.append(contenuCSV[i][4])
    groups_name.append(contenuCSV[i][5])


#PHASE 2. ON IDENTIFIE AUTOMATIQUEMENT LES CHAMPS DE CKAN: OWNER_ORG, EXTRA_ORGANISATION_PRINCIPALE ET EXT_SPATIAL
if len(sys.argv) > 1:
    modeLog                 = True
    maintenant              = datetime.strftime(datetime.now(), '%Y%m%d')
    fichierLogMaintenant    = fichierLogPrefixe + "_" + maintenant + fichierLogExtension

    dossierLog              = os.path.join(repertoire, dossierLogIntitule)
    try:
        if not (os.path.exists(dossierLog)):
            os.makedirs(dossierLog)
    except OSError as e:
        afficheErreur (separateur * 1 + "ERREUR : Création du dossier de logs impossible. Cause probable : " + str(e))
        pass

    logActuel               = open(dossierLog + SlashDossier + fichierLogMaintenant,"w+")

    if (sys.argv[1] == "@ll") :
        #moissonnage de tous les clients inscrits dans le fichier des organisations
        afficheHumeur ("# ################################################# #")
        afficheHumeur ("# ##### MOISSONNAGE INTEGRAL DES CLIENTS ESRI ##### #")
        afficheHumeur ("# ################################################# #")
        afficheHumeur ("Début des opérations : " + str(datetime.now()))

        with open(tableliee, "r") as tableCSV:
            cols    = tableCSV.readline()
            donnees = tableCSV.read().split("\n")

        for i in range(0,len(donnees)):
            moissonneClientESRI(donnees[i].split(",")[0])
    else:
        #moissonnage du client passé en paramètre
        moissonneClientESRI (sys.argv[1])

    afficheHumeur ("Fin des opérations : " + str(datetime.now()))
    logActuel.close()

else:
    afficheErreur (separateur * 1 + "ERREUR : Vous devez fournir une ville en paramètre. Réferez-vous au fichier organisations.csv")
