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
from html2text import html2text

# ##### ##### ##### ##### ##### ##### ##### #
#
# Définition des Variables locales et globales
#
# ##### ##### ##### ##### ##### ##### ##### #


#Identification des fichiers repères
fichierListeCategories      = "categories.csv"
fichierListeCategoriesPlus  = "categoriesplus.csv"
fichierListeOrganisations   = "organisations.csv"
fichierModeleESRI2CKAN      = "esriToCKAN.json"

#définition du mode Humeur. True > les mesages d'erreur et de notification sont affichés, False > mode silencieux
#lorsque modeHumeur = False, seuls les messages d'erreur ou les message des section except seront affichés éventuellement
modeHumeur  = True

#Identification du répertoire dans lequel le script se trouve et identification du template CKAN
repertoire  = os.getcwd()
found       = False
tableliee   = os.path.join(repertoire, fichierListeOrganisations)

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
    if (modeHumeur == True) :
        print (descriptionHumeur)

#moissonneClientESRI : fonction effectuant le processus entier de moissonnage pour le clientESRI spécifié
def moissonneClientESRI (clientESRI) : 
    afficheHumeur ("\n\nProcessus de moissonnage exécuté pour : " + clientESRI)

    with open(tableliee, "r") as tableCSV:
        cols    = tableCSV.readline()
        donnees = tableCSV.read().split("\n")

    for i in range(0,len(donnees)):
        if donnees[i].split(",")[0] == clientESRI:
            afficheHumeur ("---- Correspondance trouvée.")
            ownerOrg    = donnees[i].split(",")[1]
            extSpatial  = donnees[i].split(",")[2]
            arcgisUrl   = donnees[i].split(",")[3]
            found       = True
            break

    if found == True:
        outFolder = os.path.join(repertoire,"outputs" + SlashDossier + ownerOrg)
        try:
            os.makedirs(outFolder)
        except OSError:
            pass

        modele          = os.path.join(repertoire, fichierModeleESRI2CKAN)
        timestart       = datetime.datetime.now()

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
        afficheHumeur ("---- " + str(nbLayers) + " couches présentes sur OpenData.")
        afficheHumeur ("---- Début du traitement")

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

            afficheHumeur ("---- ---- ---- description : " + description.encode("utf-8"))

            #Construction de la liste des mots-clés dans une seule séquence
            #Par la suite, on écrit la liste, sans le dernier caractère, pour enlever la virgule finale (inutile)
            target['num_tags'] = len(source['dataset'][i]['keyword'])
            for j in range(0, min(len(source['dataset'][i]['keyword']),40)):
                    target['tags'][j]['display_name'] = source['dataset'][i]['keyword'][j]
                    target['tags'][j]['name'] = source['dataset'][i]['keyword'][j]
                    try:
                        tagIndex    = categories.index(source['dataset'][i]['keyword'][j])
                        categorie  += '"' + categories[tagIndex] + '",'
                    except ValueError:
                        pass

            #print(categorie)

            newTags.append("[" + categorie[:-1]+"]")

            if categorie != "":
                nombreCategories = len(categorie[:-1].split(","))
            else :
                nombreCategories = 0

            
            if (nombreCategories > 0) : 
                for nbcat in range (0, nombreCategories) :
                    categorie_actuelle = categorie[:-1].split(",")[nbcat].replace('"', '')
                    for i in range(0,len(contenuCSV)):
                        if groups_name[i] == categorie_actuelle:
                            target['groups'][nbcat]['display_name']         = groups_display_name[i]
                            target['groups'][nbcat]['description']          = groups_description[i]
                            target['groups'][nbcat]['image_display_url']    = groups_image_display_url[i]
                            target['groups'][nbcat]['title']                = groups_title[i]
                            target['groups'][nbcat]['id']                   = groups_id[i]
                            target['groups'][nbcat]['name']                 = categorie_actuelle

            #Création du morceau JSON qui ira dans le Package_list.json (index)
            listeCouches += '{"ID": ' + '"' + uniqueID + '","timestamp" : ' + '"' + source['dataset'][i]['modified'] +  '","categorie" : ' + "[" + categorie[:-1]+"]" + '},'

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
            target['author_email']                      = source['dataset'][i]['contactPoint']['hasEmail'][6:]
            target['url']                               = source['dataset'][i]['identifier']
            target['metadata_created']                  = source['dataset'][i]['issued']
            target['metadata_modified']                 = source['dataset'][i]['modified'].replace(".000Z","")

            #FORMAT WEB PAGE
            try:
                indexPage = listeFormats.index("Web page")
                target['resources'][0]['url']           = source['dataset'][i]['distribution'][indexPage]['accessURL']
                target['resources'][0]['name']          = title + " - HTML"
                target['resources'][0]['resource_type'] = "cartes"
                afficheHumeur ("---- ---- " + title)
                afficheHumeur ("---- ---- ---- catégories : " + (categorie[:-1] or "(vide)"))
            except:
                print ("xxxx xxxx xxxx Web Page format introuvable")

            #FORMAT REST
            try:
                indexREST = listeFormats.index("Esri REST")
                target['resources'][1]['url']           = source['dataset'][i]['distribution'][indexREST]['accessURL']
                target['resources'][1]['name']          = title + " - Service REST"
                target['resources'][1]['resource_type'] = "web"
            except:
                print ("xxxx xxxx xxxx REST format introuvable")

            #FORMAT GEOJSON
            try:
                indexGeoJSON = listeFormats.index("GeoJSON")
                target['resources'][2]['url']           = source['dataset'][i]['distribution'][indexGeoJSON]['downloadURL']
                target['resources'][2]['name']          = title + " - GeoJSON"
                target['resources'][2]['resource_type'] = "donnees"
            except:
                print ("xxxx xxxx xxxx GeoJSON format introuvable")

            #FORMAT CSV
            try:
                indexCSV  = listeFormats.index("CSV")
                target['resources'][3]['url']           = source['dataset'][i]['distribution'][indexCSV]['downloadURL']
                target['resources'][3]['name']          = title + " - CSV"
                target['resources'][3]['resource_type'] = "donnees"
            except:
                print ("xxxx xxxx xxxx CSV format introuvable")

            #FORMAT KML
            try:
                indexKML  = listeFormats.index("KML")
                target['resources'][4]['url']           = source['dataset'][i]['distribution'][indexKML]['downloadURL']
                target['resources'][4]['name']          = title + " - KML"
                target['resources'][4]['resource_type'] = "donnees"
            except:
                print ("xxxx xxxx xxxx KML format introuvable")

            #FORMAT SHP (ZIP)
            try:
                indexSHP  = listeFormats.index("ZIP")
                target['resources'][5]['url']           = source['dataset'][i]['distribution'][indexSHP]['downloadURL']
                target['resources'][5]['name']          = title + " - ZIP"
                target['resources'][5]['resource_type'] = "donnees"
            except:
                print ("xxxx xxxx xxxx SHP format introuvable")

            #Écriture du fichier traité
            with open(outFolder + SlashDossier + uniqueID + ".json", 'w') as sortie:
                json.dump(target, sortie)
        afficheHumeur ("---- Fin de l'écriture du CSV initial")
        afficheHumeur ("\n")

        #Écriture de l'index
        if not os.path.exists(outFolder + SlashDossier + "package_list.json"):
            afficheHumeur ("---- L'index n'existe pas. Création de l'index initial")
            listeCouches = listeCouches[:-1]
            with open(outFolder + SlashDossier + "package_list.json",'w') as index:
                index.write('{"help": "https://www.donneesquebec.ca/recherche/api/3/action/help_show?name=package_list", "success": true, "result": ['+listeCouches+']}')
        else:
            #Si l'index existe, mise à jour de l'index et changement de la valeur d'état.
            afficheHumeur ("---- L'index existe. Mise à jour de l'index.")
            
            try:
                url = "https://www.donneesquebec.ca/recherche/api/3/action/package_search?q=organization:"+clientESRI+"&rows=100000"
                response = requests.get(url)
            except:
                print ("xxxxx ERREUR : L'instance CKAN ne contient pas de données pour l'organisation " + clientESRI)
                time.sleep(3)
                sys.exit()
            ckanData    = response.json()
            ckanRes     = ckanData['result']['results']
            nbLayers    = len(ckanRes)
            afficheHumeur ("---- ---- " + str(nbLayers) + " couches sur CKAN")

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
                    newDate = datetime.datetime.strptime(newtimeStamps[i],"%Y-%m-%dT%H:%M:%S.%fZ")
                    try:
                        oldDate = datetime.datetime.strptime(oldtimestamps[indexGood],"%Y-%m-%dT%H:%M:%S")
                    except:
                        oldDate = datetime.datetime.strptime(oldtimestamps[indexGood],"%Y-%m-%dT%H:%M:%S.%f")

                    if newtimeStamps[i] > oldtimestamps[indexGood]:
                        outStates.append("MODIFICATION")
                    else:
                        outStates.append("AUCUN CHANGEMENT")

                    outCategories.append(newTags[i])
                    #afficheHumeur ("¢¢¢¢ ¢¢¢¢ ¢¢¢¢ NewTags")
                    #afficheHumeur ("¢¢¢¢ ¢¢¢¢ ¢¢¢¢ ¢¢¢¢ " + str(i) + " " + newTags[i])
                    
            listeCouches = ""
            #Création du morceau de JSON pour Package_list.json, l'index.
            for i in range(0, len(outIDs)):
                listeCouches += '{"ID": ' + '"' + str(outIDs[i]) + '","timestamp" : ' + '"' + str(outtimestamps[i]) +'","etat" : "' + str(outStates[i]) +  '","categorie" : ' + outCategories[i]  + '},'
            listeCouches = listeCouches[:-1]
            with open(outFolder + SlashDossier + "package_list.json", "w") as index:
                index.write('{"help": "https://www.donneesquebec.ca/recherche/api/3/action/help_show?name=package_list", "success": true, "result": ['+listeCouches+']}')
        timeEnd = datetime.datetime.now()-timestart

        afficheHumeur ("---- Traitement effectué en " + str(timeEnd.total_seconds()) + " secondes")
        afficheHumeur ("Fin du Processus de moissonnage de : " + clientESRI)
    else:
        print ("xxxxx ERREUR : Erreur de traitement. La ville entrée en paramètre n'existe pas ou est mal écrite (sensible à la casse)")

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
    if (sys.argv[1] == "@ll") :
        #moissonnage de tous les clients inscrits dans le fichier des organisations
        afficheHumeur ("# ################################################# #")
        afficheHumeur ("# ##### MOISSONNAGE INTEGRAL DES CLIENTS ESRI ##### #")
        afficheHumeur ("# ################################################# #")

        with open(tableliee, "r") as tableCSV:
            cols    = tableCSV.readline()
            donnees = tableCSV.read().split("\n")

        for i in range(0,len(donnees)):
            moissonneClientESRI(donnees[i].split(",")[0])
    else:
        #moissonnage du client passé en paramètre
        moissonneClientESRI (sys.argv[1])
else:
    print ("xxxxx ERREUR : Vous devez fournir une ville en paramètre. Réferez-vous au fichier organisations.csv")
