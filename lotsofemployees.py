from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Company, Base, Employee, User

engine = create_engine('sqlite:///company60.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Create dummy user
User1 = User(name="Robo", email="stevenclark314@gmail.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()


# Employees for the company Google
company1 = Company(user_id = 1, name="Google")

session.add(company1)
session.commit()

emp1 = Employee(name="Aiman", department="IT",
                     doj="2013-12-01", email="aiman@gmail.com", company=company1, user_id = 1)

session.add(emp1)
session.commit()


emp2 = Employee(name="Mazna", department="Management",
                     doj="2014-11-01", email="mazna@gmail.com", company=company1, user_id = 1)

session.add(emp2)
session.commit()

emp3 = Employee(name="Tahmina", department="Sales",
                     doj="2012-12-03", email="tahmina@gmail.com", company=company1, user_id = 1)

session.add(emp3)
session.commit()

emp4 = Employee(name="Shiba", department="HR",
                     doj="2011-12-06", email="shiba@gmail.com", company=company1, user_id = 1)

session.add(emp4)
session.commit()

# Employees for the Company Udacity
company2 = Company(user_id = 1, name="Udacity")

session.add(company2)
session.commit()


emp1 = Employee(name="John", department="IT",
                     doj="2013-10-08", email="john@gmail.com", company=company2, user_id = 1)

session.add(emp1)
session.commit()

emp2 = Employee(name="Gauri", department="IT",
                     doj="2010-08-04", email="gauri@gmail.com", company=company2, user_id = 1)

session.add(emp2)
session.commit()

print "added employee details!"