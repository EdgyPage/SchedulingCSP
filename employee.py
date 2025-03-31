class Employee:
    def __init__(self, id: str, name: str, tasks: list[str]):
        self._id = id
        self._name = name
        self._taskStatuses = tasks
        self._numApprovedTasks = 0
        self._indexApprovedTasks = []

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value: str):
        self._id = value

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value: str):
        self._name = value.lower()

    @property
    def tasks(self):
        return self._taskStatuses
    
    @tasks.setter
    def tasks(self, value: list[str]):
        n = len(value)
        statuses = [False] * n
        for i in range(n):
            if value[i] == "TRUE":
                statuses[i] = True
                self._numApprovedTasks += 1
                self._indexApprovedTasks.append(i)
        self._taskStatuses = statuses

    def __repr__(self):
        return {'id': self.id ,
                 'name': self.name,
                 'taskStatuses': self._taskStatuses}
    
    def __eq__(self, otherEmployee):
        flag = True
        if not isinstance(otherEmployee, Employee):
            flag = False
            return flag
        selfAttributes = vars(self)
        otherAttributes = vars(otherEmployee)
        flag = selfAttributes == otherAttributes
        return flag
    
    def __hash__(self):
        return hash((self.name, self.id, self.tasks))
