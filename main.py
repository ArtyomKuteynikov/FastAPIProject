import time
from functools import wraps
from itsdangerous import URLSafeTimedSerializer as Serializer
from fastapi import FastAPI, HTTPException, status
from sqlalchemy import create_engine, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

from core import find_optimal_route
from security import get_password_hash, verify_password
from sqlalchemy.orm import Session, relationship, backref
import networkx as nx

DATABASE_URL = 'sqlite:///DB.db'  # "postgresql://username:password@localhost/dbname"  # Замените на свои данные

app = FastAPI()
SECRET_KEY = "it's_secret_tssss..."

engine = create_engine(DATABASE_URL)
metadata = MetaData()
Base = declarative_base(bind=engine)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

    def generate_auth_token(self, expiration=3600):
        s = Serializer(SECRET_KEY)
        return s.dumps({'id': self.id, 'expiry_date': time.time() + expiration})

    @staticmethod
    def verify_auth_token(token):
        db = Session(bind=engine)
        s = Serializer(SECRET_KEY)
        try:
            data = s.loads(token)
            print(data)
            if data['expiry_date'] < time.time():
                return None
        except:
            return None
        user = db.query(User).filter(User.id == data['id']).first()
        db.close()
        return user


class Place(Base):
    __tablename__ = "places"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    weight = Column(Integer)
    start = Column(Integer)
    end = Column(Integer)


class Route(Base):
    __tablename__ = "routes"
    id = Column(Integer, primary_key=True, index=True)
    place1 = Column(Integer, ForeignKey('places.id', ondelete='CASCADE'))
    place2 = Column(Integer, ForeignKey('places.id', ondelete='CASCADE'))
    weight = Column(Integer)


class Result(Base):
    __tablename__ = "result"
    id = Column(Integer, primary_key=True, index=True)
    weight = Column(Integer)
    route = Column(String)


engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)


@app.post("/register")
async def register(username: str, password: str):
    db = Session(bind=engine)
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered"
        )

    hashed_password = get_password_hash(password)
    new_user = User(username=username, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    return {"message": "User registered successfully"}


@app.post("/token")
async def login_for_access_token(username: str, password: str):
    db = Session(bind=engine)
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    db.close()
    return {"access_token": user.generate_auth_token()}


@app.get("/add-place")
async def add_place(token: str, name: str, weight: int, start: int, end: int):
    user = User.verify_auth_token(token)
    if user:
        db = Session(bind=engine)
        existing_user = db.query(Place).filter(Place.name == name).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Place already exist"
            )
        new_place = Place(name=name, weight=weight, start=start, end=end)
        db.add(new_place)
        db.commit()
        db.refresh(new_place)
        db.close()
        return {'message': f"Place {new_place.id} added"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect token",
        )


@app.get("/edit-place")
async def edit_place(token: str, id: int, name: str, weight: int, start: int, end: int):
    user = User.verify_auth_token(token)
    if user:
        db = Session(bind=engine)
        place = db.query(Place).filter(Place.id == id).update(
            {'name': name, 'weight': weight, 'start': start, 'end': end})
        db.commit()
        db.close()
        return {'message': f"Place {place} edited"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect token",
        )


@app.get("/delete-place")
async def delete_place(token: str, id: int):
    user = User.verify_auth_token(token)
    print(id)
    if user:
        db = Session(bind=engine)
        place = db.query(Place).filter(Place.id == id).delete()
        db.commit()
        db.close()
        return {'message': f"Place {id} deleted"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect token",
        )


@app.get("/add-route")
async def add_route(token: str, weight: int, place1: int, place2: int):
    user = User.verify_auth_token(token)
    if user:
        db = Session(bind=engine)
        new_route = Route(weight=weight, place1=place1, place2=place2)
        db.add(new_route)
        db.commit()
        db.refresh(new_route)
        db.close()
        return {'message': f"Route {new_route.id} added"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect token",
        )


@app.get("/edit-route")
async def edit_route(token: str, id: int, weight: int, place1: int, place2: int):
    user = User.verify_auth_token(token)
    if user:
        db = Session(bind=engine)
        route = db.query(Route).filter(Route.id == id).update({'weight': weight, 'place1': place1, 'place2': place2})
        db.commit()
        db.close()
        return {'message': f"Route {route} edited"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect token",
        )


@app.get("/delete-route")
async def delete_route(token: str, id: int):
    user = User.verify_auth_token(token)
    if user:
        db = Session(bind=engine)
        route = db.query(Route).filter(Route.id == id).delete()
        db.commit()
        db.close()
        return {'message': f"Route {id} deleted"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect token",
        )


@app.get("/create-route")
async def delete_route(token: str, start: int, end: int, weight_limit: int):
    user = User.verify_auth_token(token)
    if user:
        db = Session(bind=engine)
        G = nx.DiGraph()
        for i in db.query(Place).filter().all():
            G.add_node(i.name, weight=i.weight, time_window=(i.start, i.end))
        for i in db.query(Route).filter().all():
            place1 = db.query(Place).filter(Place.id == i.place1).first().name
            place2 = db.query(Place).filter(Place.id == i.place2).first().name
            G.add_edge(place1, place2, weight=i.weight)
        start = db.query(Place).filter(Place.id == start).first().name
        end = db.query(Place).filter(Place.id == end).first().name
        weight_limit = weight_limit
        optimal_route, total_delivery_time = find_optimal_route(G, start, end, weight_limit)
        new_route = Result(weight=total_delivery_time, route=optimal_route)
        db.add(new_route)
        db.commit()
        db.refresh(new_route)
        db.close()
        return {'message': f"Optimal route: {optimal_route}, total delivery time: {total_delivery_time}"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect token",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
