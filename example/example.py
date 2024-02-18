from __future__ import annotations
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Type, Union

from enum import Enum, auto

"""
consider the case where you want to do

for entity in world.query(component | components, with=Position, without=Velocity):
    entity.Position += entity.Velocity

for _, pos, vel in world.query(Position, Velocity):
    pos += vel

"""

# Uncomment these lines to make the example work without installing the package
import sys

sys.path.append("../")
from phecs import phecs


class Point:
    def __init__(self) -> None:
        self.x = 0.0
        self.y = 0.0


################    DEFINE YOUR COMPONENTS    ################


class Name:
    def __init__(self, name: str) -> None:
        self.name = name


class Velocity:
    def __init__(self) -> None:
        self.vel = Point()


class Position:
    def __init__(self) -> None:
        self.pos = Point()


################    DEFINE YOUR SYSTEMS    ################
def do_physics(ecs):
    for _, pos, vel in ecs.query(Position, Velocity):
        pos += vel


################    FILL YOUR WORLD AND USE IT    ################


class Error(Enum):
    NoSuchEntity = auto()
    NoSuchComponent = auto()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class NoSuchEntity(Exception):
    pass


class NoSuchComponent(Exception):
    pass


class Entity:
    def __init__(self, id):
        self.__id = id

    def __hash__(self) -> int:
        return hash(self.__id)

    def __repr__(self) -> str:
        return f"Entity: {self.__id.__repr__()}"

    def __eq__(self, other_entity: Entity) -> bool:
        return self.__id == other_entity.__id


class InternalEntity:
    def __init__(self, entity: Entity):
        self.entity: Entity = entity
        self.components: dict[Type, Any] = {}


"""
Naming Guide for if you want to shorten a variable in a comprehension:
e = entity
ie = internal_entity
es = entities
c = component
cs = components
"""


class World:
    def __init__(self) -> None:
        self.next_entity_id: int = 0
        self.entities: Dict[InternalEntity] = {}

    def spawn(self, *components: Tuple[Any, ...]) -> Entity:
        entity = Entity(self.next_entity_id)
        self.next_entity_id += 1
        internal_entity = InternalEntity(entity)
        self.entities[entity] = internal_entity
        for component in components:
            internal_entity.components[type(component)] = component
        return entity

    def spawn_at(self, entity: Entity, *components: Tuple[Any, ...]) -> None:
        internal_entity = InternalEntity(entity)
        self.entities[entity] = internal_entity
        for component in components:
            internal_entity.components[type(component)] = component

    def despawn(self, entity: Entity) -> Optional[Error.NoSuchEntity]:
        if entity in self.entities:
            del self.entities[entity]
        else:
            return Error.NoSuchEntity

    def clear(self) -> None:
        self.entities.clear()

    def contains(self, entity: Entity) -> bool:
        return entity in self.entities

    def find(
        self,
        *component_types: Tuple[Type, ...],
        has: Optional[Type | List[Type]] | Tuple[Type, ...] = None,
        without: Optional[Type | List[Type]] | Tuple[Type, ...] = None,
    ) -> Iterator[tuple]:
        has = (
            has
            if isinstance(has, (list, tuple))
            else [has] if has is not None else None
        )
        without = (
            without
            if isinstance(without, (list, tuple))
            else [without] if without is not None else None
        )

        for internal_entity in self.entities.values():
            if has and not all(c in internal_entity.components for c in has):
                continue
            if without and any(c in internal_entity.components for c in without):
                continue
            if all(c in internal_entity.components for c in component_types):
                yield internal_entity.entity, tuple(
                    internal_entity.components[c] for c in component_types
                )

    def find_on(
        self,
        entity: Entity,
        *component_types: Tuple[Type, ...],
        has: Optional[Type | List[Type] | Tuple[Type, ...]] = None,
        without: Optional[Type | List[Type] | Tuple[Type, ...]] = None,
    ) -> Optional[tuple]:
        if entity not in self.entities:
            return None
        internal_entity = self.entities[entity]

        if has:
            if isinstance(has, (list, tuple)):
                if not all(c in internal_entity.components for c in has):
                    return None
            else:
                if has not in internal_entity.components:
                    return None

        if without:
            if isinstance(without, (list, tuple)):
                if any(c in internal_entity.components for c in without):
                    return None
            else:
                if without in internal_entity.components:
                    return None

        if all(c in internal_entity.components for c in component_types):
            return (
                internal_entity.entity,
                tuple(internal_entity.components[c] for c in component_types),
            )

        return None

    def get(self, entity: Entity, component_type: Type) -> Any | None:
        if entity in self.entities:
            if component_type in self.entities[entity].components:
                return self.entities[entity].components[component_type]
        return None

    def satisfies(
        self,
        entity: Entity,
        has: Optional[Type | List[Type]] | Tuple[Type, ...] = None,
        without: Optional[Type | List[Type]] | Tuple[Type, ...] = None,
    ) -> bool:
        if entity not in self.entities:
            return False
        internal_entity = self.entities[entity]

        if has:
            if isinstance(has, (list, tuple)):
                if not all(c in internal_entity.components for c in has):
                    return False
            else:
                if has not in internal_entity.components:
                    return False

        if without:
            if isinstance(without, (list, tuple)):
                if any(c in internal_entity.components for c in without):
                    return False
            else:
                if without in internal_entity.components:
                    return False

        return True

    def iter(self):
        for entity in self.entities.keys():
            yield entity

    def insert(
        self, entity: Entity, *components: Tuple[Any, ...]
    ) -> None | Error.NoSuchEntity:
        if entity in self.entities:
            for component in components:
                self.entities[entity].components[type(component)] = component
        else:
            return Error.NoSuchEntity

    def remove(self, entity: Entity, *component_types: Tuple[Any, ...]) -> None:
        if entity in self.entities:
            internal_entity = self.entities[entity]
            for component_type in component_types:
                if component_type in internal_entity.components:
                    del internal_entity.components[component_type]

    def take(self, entity: Entity) -> tuple:
        if entity in self.entities:
            internal_entity = self.entities[entity]
            components = tuple(internal_entity.components.values())
            self.despawn(entity)
            return components
        return tuple()

    def iter(self) -> Iterator[Entity]:
        for internal_entity in self.entities:
            yield internal_entity.entity


"""
need:
    spawn
    despawn
    insert(e, components)
    insert_one(e, component)
    remove(e, componentTypes)
    remove_one(e, componentType)
    with # moved into has
    without # moved into has
    ecs.clear, despawns all entities
    ecs.get(e, componentType)

want:
    ecs.contains(e) => true / false
    ecs.spawn_at(a)
    ecs.satisfies(e, components)

maybe_need:
    take (despawn entity, returning all its components in tuple)
        for moving entity between world easily


maybe not need:
    query_one 
"""


ecs = World()
a = ecs.spawn(Position(), Velocity(), Name("e1"))
b = ecs.spawn(Position(), Velocity(), Name("e2"))
c = ecs.spawn(Position(), Velocity())
c = ecs.spawn(Position())

for e, pos, vel in ecs.query((Position, Velocity)):
    print(e)

ecs.despawn(c)

while True:
    do_physics(ecs)
