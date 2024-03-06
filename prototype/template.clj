Scenario: <scenario name>

Given/And 


    [
        the <entity name>
        ["<entity instance>"]
    ]
    /
    [
        the <property name> 
        ["<property instance>"] 
        {of/from/in/on/at}
        the <entity name>
        ["<entity instance>"]
    ] 


    {is/is not/are/are not}

    
    [
        [in]
        <state name>
    ]
    /
    [
        equal to/greater than/less than 
        <property value>
    ]

When/And I 
    [do/do not] 
    <action name> 
    [<action value>]


    [
        the <entity name>
        ["<entity instance>"]
    ]
    /
    [
        the <property name> 
        ["<property instance>"] 
        {of/from/in/on/at}
        the <entity name>
        ["<entity instance>"]
    ] 


    [
        within 
        <time variable value> 
        <time variable>
    ]

[
    And I 
        [do/do not]
        concurrently
        <action name>
        [<action value>]

        [
            the <entity name>
            ["<entity instance>"]
        ]
        /
        [
            the <property name>
            ["<property instance>"]
            {of/from/in/on/at}
            the <entity name> 
            ["<entity instance>"]
        ]

]

Then/And 
    [
        the <entity name> 
        ["<entity instance>"]
    ]
    /
    [
        the <property name>
        ["<property instance>"]
        {of/from/in/on/at}
        the <entity name>
        ["<entity instance>"]
    ]


    {is/is not/are/are not}


    [
        [in] <state name>
    ]
    /
    [
        equal to/greater than/less than 
        <property value>
    ]