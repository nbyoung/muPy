import re

from . import syntax

class TagRayError(ValueError): pass

class TagRay:

    regex = r'[+-]' + syntax.Identifier.regex

    @classmethod
    def fromString(cls, string):
        if string in ('', '+', '-', ): return cls.fromTags()
        string = '+' + string if string[0] not in ('+', '-', ) else string
        if not re.fullmatch(f'({TagRay.regex})+', string):
            raise TagRayError(f'Invalid tag string {string}')
        bothTags = [t for t in re.split(f'({TagRay.regex})', string) if len(t)]
        return cls.fromTags(
            [t[1:] for t in bothTags if t[0] == '+'],
            [t[1:] for t in bothTags if t[0] == '-'],
        )

    @classmethod
    def fromTags(cls, plusTags=(), minusTags=()):
        plusTagSet = frozenset(plusTags)
        minusTagSet = frozenset(minusTags)
        if bool(minusTagSet):
            raise NotImplementedError("Minus tags ('-tag') not implemented")
        intersection = plusTagSet & minusTagSet
        if intersection: raise TagRayError(f'Plus {plusTagSet} and Minus {minusTagSet} cannot overlap {intersection}')
        return cls(plusTagSet, minusTagSet)

    def __init__(self, plusTagSet=frozenset(), minusTagSet=frozenset()):
        self._plusTagSet = frozenset(plusTagSet)
        if bool(minusTagSet):
            raise NotImplementedError("Minus tags ('-tag') not implemented")
        self._minusTagSet = frozenset(minusTagSet)

    def __str__(self):
        def sign(s, ts):
            tags = list(ts)
            tags.sort()
            return ''.join([s + t for t in tags])
        return (
            sign("+", self._plusTagSet)
            +
            sign("-", self._minusTagSet)
        )

    def plus(self, *tagRays):
        return TagRay(
            self._plusTagSet.union(*[tR._plusTagSet for tR in tagRays]),
            self._minusTagSet.union(*[tR._minusTagSet for tR in tagRays]),
        )
    # Apply to MPY_TAGS, args.tags, and target.tags in Kit.fromBOM()+

    def __len__(self): return len(self._plusTagSet)

    def __lt__(self, other): return self._plusTagSet < other._plusTagSet
    def __le__(self, other): return self._plusTagSet <= other._plusTagSet
    def __eq__(self, other): return self._plusTagSet == other._plusTagSet
    def __neq__(self, other): return not self._plusTagSet == other._plusTagSet
    def __ge__(self, other): return not self._plusTagSet < other._plusTagSet
    def __gt__(self, other): return not self._plusTagSet <= other._plusTagSet

class TagIndexError(ValueError): pass

class _Entry:
    def __init__(self, tagRay, item):
        self._tagRay = tagRay
        self._item = item
    def __len__(self): return len(self._tagRay)
    @property
    def tagRay(self): return self._tagRay
    @property
    def item(self): return self._item

class TagIndex:

    def __init__(self, tagRayItems=()):
        self._entries = []
        for tagRay, item in tagRayItems: self.add(tagRay, item)

    def __iter__(self): return iter(self._entries)

    def __bool__(self): return bool(len(self._entries))

    def add(self, tagRay, item):
        if tagRay in [e.tagRay for e in self._entries]:
            raise TagIndexError(f'Duplicate tags {tagRay}')
        else:
            self._entries.append(_Entry(tagRay, item))

    def max(self, tagRay):
        entries = sorted(
            [entry for entry in self._entries if entry.tagRay <= tagRay],
            key=len,
            reverse=True,
        )
        if 0 == len(entries):
            raise TagIndexError(f"Entries for '{tagRay}' not found in {[e.tagRay for e in entries]}")
        elif (
                1 < len(entries)
                and
                len(entries[0]) == len(entries[1])
        ):
            raise TagIndexError(
                f'Duplicates {entries[0].tagRay} and {entries[1].tagRay} for {tagRay}'
            )
        return entries[0].item

    @property
    def count(self): return len(self._entries)
