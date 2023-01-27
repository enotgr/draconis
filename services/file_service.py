import json

class FileService:
  def getJsonObjByPath(self, path):
    jsonFile = None
    
    try:
      file = open(path, 'r', encoding='utf-8')
      jsonFile = json.load(file)
      file.close()
    except:
      print('Error: cannot open json file.')
    return jsonFile

  def saveJsonFile(self, jsonObj, path):
    try:
      file = open(path, 'w', encoding='utf-8')
      json.dump(jsonObj, file, indent = 2)
      file.close()
      return True
    except:
      print('Error: cannot save json file.')
      return False
    
  def getTextFileByPath(self, path):
    text = ''
    try:
      file = open(path, 'r', encoding='utf-8')
      text = file.read()
    except:
      print('Error: cannot read text file.')
    return text

fileService = FileService()
