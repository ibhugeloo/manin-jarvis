# Décisions structurantes

> **Template.** Copiez en `decisions.md`. C'est le **journal des choix tranchés et datés** :
> la source de vérité quand une nouvelle idée risque de contredire un choix passé.
> Auto-chargé → garder **dense** (Décision + Pourquoi en 3-5 lignes). Le détail long va ailleurs.

**Règles :**
- Une décision révisée ? **Garder l'ancienne entrée**, ajouter une nouvelle datée. Jamais réécrire l'historique.
- Plus récent en haut.
- Si ce fichier grossit trop (auto-load coûteux) : archiver les vieilles entrées dans
  `decisions-archive.md` (non auto-chargé) et le détail long dans `decisions-detail.md`.

---

## AAAA-MM-JJ — <Titre court de la décision>

**Décision** : <ce qui a été tranché, concrètement. 2-3 phrases.>

**Pourquoi** : <la raison profonde, les contraintes, ce que ça remplace. 2-3 phrases.
Mentionner l'alternative écartée si elle risque de revenir sur le tapis.>

---

## AAAA-MM-JJ — <Exemple : Déploiement front sur la plateforme X>

**Décision** : les fronts en prod vont sur `<plateforme>` ; l'environnement de dev/staging
reste sur `<infra interne>`. Les bases critiques sur `<service géré>`.

**Pourquoi** : la prod doit tenir un SLA que l'infra interne ne garantit pas ; séparer rend
explicite l'engagement de service. Alternative écartée : tout self-héberger (trop de risque
pour du client qui paie).

---

> **Astuce :** écrivez une décision **au moment où vous la prenez**, pas après. Le coût
> (3 lignes) est dérisoire face au coût de re-débattre un choix oublié trois mois plus tard.
