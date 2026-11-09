# Consignes pour Claude

- Toujours répondre à Etienne en français.

## Skill find-skills

Au début de chaque session, et chaque fois qu'Etienne le demande :

1. Vérifier si la skill est installée : `test -e ~/.agents/skills/find-skills/SKILL.md`
2. Si elle est absente (ou sur demande explicite), l'installer :

   ```bash
   npx -y skills add vercel-labs/skills@find-skills -g -y
   ```

La même commande est aussi dans le script de configuration de l'environnement cloud
« Default » ; cette consigne sert de filet de sécurité si ce script n'a pas tourné.
