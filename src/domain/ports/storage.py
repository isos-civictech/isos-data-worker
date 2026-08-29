"""
Port : déposer un fichier brut dans un stockage objet.

Le fichier tel que l'Assemblée l'a publié est conservé pour la traçabilité : il
permet de rejouer un parsing après correction d'un bug, et de prouver ce qu'on a
réellement reçu. Rien ne le relit en fonctionnement normal.

Deux implémentations : `GarageS3Storage` (boto3) et `NoopStorage`, choisie
automatiquement quand aucun S3 n'est configuré — c'est le cas dans le cluster
aujourd'hui. Tout le reste du pipeline fonctionne à l'identique dans les deux
cas, ce qui est précisément l'intérêt d'avoir un port ici.
"""
from abc import ABC, abstractmethod


class RawStoragePort(ABC):
    @abstractmethod
    async def put(
        self,
        key: str,
        body: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Dépose `body` sous `key` et renvoie la clé effectivement utilisée.

        La clé suit la convention documentée dans les entités, par exemple
        `raw/debates/{legislature}/{year}/{month}/{uid}.xml`.
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Vrai si l'objet est déjà présent (évite un renvoi inutile)."""
        ...
