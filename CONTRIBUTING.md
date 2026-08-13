Simple over Easy
Usability over Performance
Python Interoperability 

Instead of taking a single config object in __init__, expose parameters directly.  

Follow the Law of Demeter. An object should have limited knowledge of other objects and only talk to its immediate friends.
    Core Rules:
        A method inside an object should only call methods on:
        itself
        Objects passed in as arguments to the method
        Objects it creates inside the method
        Its direct component objects (fields/member variables)

    Avoiding Violations:
        No method chaining: Avoid long chains like object.getA().getB().doSomething(), often called "train wrecks".
        Tell, don't ask: Ask an object to perform a task directly rather than reaching into its internal structure to pull out data.
        Loose coupling: Keeps classes independent so changes in one sub-component do not break unrelated parts of the program.