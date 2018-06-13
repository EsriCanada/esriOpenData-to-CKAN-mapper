
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
import urllib, datetime, time
from html2text import html2text
#Identification du répertoire dans lequel le script se trouve et identification du template CKAN
repertoire = os.getcwd()
found = False

#PHASE 2. ON IDENTIFIE AUTOMATIQUEMENT LES CHAMPS DE CKAN: OWNER_ORG, EXTRA_ORGANISATION_PRINCIPALE ET EXT_SPATIAL
if len(sys.argv) > 1:
    print "Vous executez pour: " + sys.argv[1]
    tableliee = os.path.join(repertoire,"organisations.csv")
    with open(tableliee, "r") as tableCSV:
        cols = tableCSV.readline()
        donnees = tableCSV.read().split("\n")
    for i in range(0,len(donnees)):
        if donnees[i].split(",")[0] == sys.argv[1]:
            print "Correspondance trouvee"
            ownerOrg = donnees[i].split(",")[1]
            extSpatial = donnees[i].split(",")[2]
            arcgisUrl = donnees[i].split(",")[3]
            found = True
            break
    if found == True:
        outFolder = os.path.join(repertoire,"outputs")
        try:
            os.makedirs(outFolder)
        except OSError:
            pass
        modele= os.path.join(repertoire, "esriToCKAN.json")
        timestart = datetime.datetime.now()
        #Chargement de l'URL Open Data
        url = arcgisUrl
        response = urllib.urlopen(url)
        source = json.loads(response.read())
        #Affichage du nombre de jeux de données répertoriés par data.json
        nbLayers = len(source['dataset'])
        listeCouches = ""
        listeFormats = []
        #Création d'une liste d'ID uniques
        newIDs = []
        newtimeStamps = []
        print str(nbLayers) + " couches presentes sur OpenData. Debut du traitement"
        #Boucle qui parcours les datastes un après l'autre.
        for i in range(0, nbLayers):
            with open(modele) as data_file:
                target = json.load(data_file)
            listeFormats=[]
            #Idenficiations des formats des datasets
            for k in range(0,len(source['dataset'][i]['distribution'])):
                listeFormats.append(source['dataset'][i]['distribution'][k]['format'])
            #Récupération de l'ID unique et des champs communs à la ressource.
            uniqueID = source['dataset'][i]['identifier'].split("/")[len(source['dataset'][i]['identifier'].split("/"))-1]
            newIDs.append(uniqueID)
            newtimeStamps.append(source['dataset'][i]['modified'])
            target['title'] = source['dataset'][i]['title']
            description = source['dataset'][i]['description']
            target['description'] = description
            target['name'] = uniqueID
            title = target['title']
            #Création du morceau JSON qui ira dans le Package_list.json (index)
            listeCouches += '{"ID": ' + '"' + uniqueID + '","timestamp" : ' + '"' + source['dataset'][i]['modified'] +'"},'
            #Construction de la liste des mots-clés dans une seule séquence
            #Par la suite, on écrit la liste, sans le dernier caractère, pour enlever la virgule finale (inutile)
            target['num_tags'] = len(source['dataset'][i]['keyword'])
            for j in range(0, min(len(source['dataset'][i]['keyword']),40)):
                    target['tags'][j]['display_name'] = source['dataset'][i]['keyword'][j]
                    target['tags'][j]['name'] = source['dataset'][i]['keyword'][j]
            #logique de validation qui supprimera les TAGS laissés vides.
            correct = False;
            while correct != True:
                if target['tags'][len(target['tags'])-1]['name']== "":
                        target['tags'].remove(target['tags'][len(target['tags'])-1])
                else:
                    correct = True;
            target['author'] = source['dataset'][i]['contactPoint']['fn']
            target['extras_organisation_principale'] = sys.argv[1]
            target['owner_org'] = ownerOrg
            target["ext_spatial"]=extSpatial
            target['author_email'] = source['dataset'][i]['contactPoint']['hasEmail'][6:]
            target['url'] = source['dataset'][i]['identifier']
            target['metadata_created'] = source['dataset'][i]['issued']
            target['metadata_modified'] = source['dataset'][i]['modified']
            #FORMAT WEB PAGE
            try:
                indexPage = listeFormats.index("Web page")
                target['resources'][0]['url'] = source['dataset'][i]['distribution'][indexPage]['accessURL']
                target['resources'][0]['name'] = title + " - HTML"
                print title
            except:
                print "Web Page format introuvable"
            #FORMAT REST
            try:
                indexREST = listeFormats.index("Esri REST")
                target['resources'][1]['url'] = source['dataset'][i]['distribution'][indexREST]['accessURL']
                target['resources'][1]['name'] = title + " - Service REST"
            except:
                print "REST format introuvable"
            #FORMAT GEOJSON
            try:
                indexGeoJSON = listeFormats.index("GeoJSON")
                target['resources'][2]['url'] = source['dataset'][i]['distribution'][indexGeoJSON]['downloadURL']
                target['resources'][2]['name'] = title + " - GeoJSON"
            except:
                print "GeoJSON format introuvable"
                #FORMAT CSV
            try:
                indexCSV  = listeFormats.index("CSV")
                target['resources'][3]['url'] = source['dataset'][i]['distribution'][indexCSV]['downloadURL']
                target['resources'][3]['name'] = title + " - CSV"
            except:
                print "CSV format introuvable"
            #FORMAT KML
            try:
                indexKML  = listeFormats.index("KML")
                target['resources'][4]['url'] = source['dataset'][i]['distribution'][indexKML]['downloadURL']
                target['resources'][4]['name'] = title + " - KML"
            except:
                print "KML format introuvable"
            #FORMAT SHP (ZIP)
            try:
                indexSHP  = listeFormats.index("ZIP")
                target['resources'][5]['url'] = source['dataset'][i]['distribution'][indexSHP]['downloadURL']
                target['resources'][5]['name'] = title + " - ZIP"
            except:
                print "SHP format introuvable"
            #Écriture du fichier traité
            with open(outFolder + "\\" + uniqueID + ".json", 'w') as sortie:
                json.dump(target, sortie)
        print "Fini l'ecriture du CSV initial"
        #Écriture de l'index
        if not os.path.exists(outFolder + "\\" + "package_list.json"):
            print "L'Index n'existe pas. Création de l'index initial"
            listeCouches = listeCouches[:-1]
            with open(outFolder + "\\" + "package_list.json",'w') as index:
                index.write('{"help": "https://www.donneesquebec.ca/recherche/api/3/action/help_show?name=package_list", "success": true, "result": ['+listeCouches.encode('utf-8')+']}')
        else:
            #Si l'index existe, mise à jour de l'index et changement de la valeur d'état.
            print "L'index existe. Mise a jour de l'index."
            
            try:
                url = "https://www.donneesquebec.ca/recherche/api/3/action/package_search?q=organization:"+sys.argv[1]+"&rows=100000"
                response = urllib.urlopen(url)
            except:
                print "L'Instance CKAN ne contient pas de donnees pour l'organisation " + sys.argv[1]
                time.sleep(3)
                sys.exit()
            ckanData = json.loads(response.read())
            ckanRes = ckanData['result']['results']
            nbLayers = len(ckanRes)
            print str(nbLayers) + " couches sur CKAN"
            oldIDs = []
            oldtimestamps = []
            for i in range(0, nbLayers):
                if ckanRes[i]['name'].find("_")!= -1:
                    oldIDs.append(ckanRes[i]['name'])
                    oldtimestamps.append(ckanRes[i]['metadata_modified'])


            outIDs = []
            outtimestamps = []
            outStates = []
            
            #Identification des ajouts
            for i in range(0, len(newIDs)):
                if newIDs[i] in oldIDs:
                    pass
                else:
                    outIDs.append(newIDs[i])
                    outtimestamps.append(newtimeStamps[i])
                    outStates.append("AJOUT")
            #Identification des suppressions
            for i in range(0, len(oldIDs)):
                if oldIDs[i] in newIDs:
                    pass
                else:
                    outIDs.append(oldIDs[i])
                    outtimestamps.append(oldtimestamps[i])
                    outStates.append("SUPPRESSION")

            #Identifications des plus récents (mis à jour)
            for i in range(0, len(newIDs)):
                if newIDs[i] in oldIDs:
                    outIDs.append(newIDs[i])
                    outtimestamps.append(newtimeStamps[i])
                    indexGood = oldIDs.index(newIDs[i])
                    newDate = datetime.datetime.strptime(newtimeStamps[i],"%Y-%m-%dT%H:%M:%S.%fZ")
                    oldDate = datetime.datetime.strptime(oldtimestamps[indexGood],"%Y-%m-%dT%H:%M:%S.%f")
                    if newtimeStamps[i] > oldtimestamps[indexGood]:
                        outStates.append("MODIFICATION")
                    else:
                        outStates.append("AUCUN CHANGEMENT")
                    
            listeCouches = ""
            #Création du morceau de JSON pour Package_list.json, l'index.
            for i in range(0, len(outIDs)):
                listeCouches += '{"ID": ' + '"' + str(outIDs[i]) + '","timestamp" : ' + '"' + str(outtimestamps[i]) +'","etat" : "' + str(outStates[i]) +  '"},'
            listeCouches = listeCouches[:-1]
            with open(outFolder + "\\package_list.json", "w") as index:
                index.write('{"help": "https://www.donneesquebec.ca/recherche/api/3/action/help_show?name=package_list", "success": true, "result": ['+listeCouches.encode('utf-8')+']}')
        timeEnd = datetime.datetime.now()-timestart
        print "Traitement effectue en " + str(timeEnd.total_seconds()) + " secondes"
        print "FINI"
    else:
        print "Erreur de traitement. La ville entree en parametre n'existe pas ou est mal ecrite"
else:
    print "ERREUR: Vous devez fournir une ville en parametre. Referez-vous au fichier organisations.csv"