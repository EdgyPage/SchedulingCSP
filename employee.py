class Employee:
    def __init__(self, id: str, name: str, tasks:list[str], taskStatuses: list[bool]):
        self._id = id
        self._name = name
        self._numApprovedTasks = 0
        self._indexApprovedTasks = [0]
        self.tasks = tasks
        self.taskStatuses = taskStatuses

    @property
    def id(self):
        return self._id

    @property
    def indexApprovedTasks(self):
        return self._indexApprovedTasks
    
    @property
    def numApprovedTasks(self):
        return self._numApprovedTasks
    
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
    def taskStatuses(self):
        return self._taskStatuses
    
    @taskStatuses.setter
    def taskStatuses(self, value: list[bool]):
        n = len(value)
        statuses = [False] * n
        if len(statuses) != len(self.tasks):
            raise ValueError("Amount of functions does not match amount of approvals!")
        for i in range(n):
            if value[i] == True:
                statuses[i] = True
                self._numApprovedTasks += 1
                self._indexApprovedTasks.append(i+1)
        self._taskStatuses = statuses

    @property
    def tasks(self):
        return self._tasks
    
    @tasks.setter
    def tasks(self, value: list[str]):
        self._tasks = value

    def __repr__(self):
        return f"""
                id: {self.id}, 
                 name: {self.name}, 
                 taskStatuses: {self._taskStatuses}
                """
    
    def __lt__(self, otherEmployee):
        return self.id < otherEmployee.id

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
        return hash((self.name, self.id, tuple(self.taskStatuses)))
