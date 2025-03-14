# Guide de dépannage - AssistProf

## Résolution de l'erreur "ModuleNotFoundError: No module named 'flask'"

Si vous rencontrez cette erreur, cela signifie que Flask n'est pas correctement installé. Voici comment résoudre ce problème:

### 1. Vérifiez que l'environnement virtuel est activé

Votre terminal devrait afficher `(venv)` au début de la ligne de commande.

Si ce n'est pas le cas, activez l'environnement virtuel:
```bash
# Pour Windows
venv\Scripts\activate

# Pour Linux/MacOS
source venv/bin/activate
```

### 2. Installez les dépendances

Assurez-vous que les dépendances sont correctement installées:
```bash
pip install -r requirements.txt
```

### 3. Installation directe de Flask

Si le problème persiste, essayez d'installer Flask directement:
```bash
pip install flask
```

### 4. Vérifiez l'installation

Pour vérifier si Flask est bien installé:
```bash
pip list | grep flask
# ou sur Windows
pip list | findstr flask
```

### 5. Problèmes d'environnement Python

Si vous avez plusieurs versions de Python installées, assurez-vous d'utiliser la bonne:
```bash
python --version
# Si nécessaire, utilisez python3 explicitement
python3 -m pip install flask
```

### 6. Redémarrage du terminal

Parfois, un simple redémarrage du terminal après l'installation des packages peut résoudre le problème.

## Résolution de l'erreur "ModuleNotFoundError: No module named 'MySQLdb'"

Si vous rencontrez cette erreur, cela signifie que le module `MySQLdb` n'est pas correctement installé. Voici comment résoudre ce problème:

### 1. Installez `mysqlclient`

Assurez-vous que `mysqlclient` est installé:
```bash
pip install mysqlclient
```

### 2. Vérifiez l'installation

Pour vérifier si `mysqlclient` est bien installé:
```bash
pip list | grep mysqlclient
# ou sur Windows
pip list | findstr mysqlclient
```

### 3. Problèmes d'environnement Python

Si vous avez plusieurs versions de Python installées, assurez-vous d'utiliser la bonne:
```bash
python --version
# Si nécessaire, utilisez python3 explicitement
python3 -m pip install mysqlclient
```

### 4. Redémarrage du terminal

Parfois, un simple redémarrage du terminal après l'installation des packages peut résoudre le problème.
