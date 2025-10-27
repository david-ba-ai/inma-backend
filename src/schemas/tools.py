from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field 


class FinancialSituation(BaseModel):
    month_revenues: int = Field(
        default=None, 
        description="Ingresos mensuales de diferentes fuentes"
    )
    is_employed: Optional[bool] = Field(
        default=None, 
        description="Si el usuario tiene un empleo"
    )
    type_employment: str = Field(
        default=None, 
        description="Campo profesional del usuario"
    )
    type_contract: str = Field(
        default=None, 
        description="Tipo de contrato de trabajo (autónomo, por cuenta ajena, pluriempleado, desempleado)"
    )
    temporary_employment: str = Field(
        default=None, 
        description="Tipo de contrato (temporal, indefinido, desempleado)"
    )
    savings: int = Field(
        default=None,
        description="Cuantía de ahorros"
    )
    have_loans: int = Field(
        default=None,
        description="Si el usuario tiene algún prestamo"
    )
    amount_loans: int = Field(
        default=None,
        description="La cuantía a devolver del préstamo"
    )
    is_propietary: Optional[bool] = Field(
        default=None,
        description="Si el usuario es propietario de algún inmueble"
    )
    monthly_expenses: int = Field(
        default=False,
        description="Cuánto puede permitirse gastarse al mes"
    )
    

class QAToolModel(BaseModel):
    missing_fields: List[str] = Field(
        default_factory=list, 
        description="Campos faltantes para ejecutar la consulta"
    )
    last_query: Optional[str] = Field(
        default=None,
        description="La última consulta SQL ejecutada o intentada"
    )
    last_modify_query: Optional[str] = Field(
        default=None,
        description="La última consulta SQL ejecutada o intentada"
    )
    last_result: Dict[str, Any] = Field(
        default_factory=dict, 
        description="La última respuesta dada por la base de datos, parseada con nombres de columnas"
    )
    searched_inms: List[int] = Field(
        default_factory=list, 
        description="Lista de IDs de inmuebles ya buscados"
    )
    presented_inms: List[int] = Field(
        default_factory=list, 
        description="Lista de IDs de inmuebles ya presentados"
    )
    inm_localization: Optional[tuple[float, float]] = Field(
        default=None, 
        description="Localización (latitud, longitud) indicada para búsqueda generada en la animación."
    )
    buffer_input: str = Field(
        default="", 
        description="Input anterior cuando hay campos requeridos."
    )
    more_info: bool = Field(
        default=False, 
        description="Indica si se le he preguntado al usuario por información auxiliar sobre el inmueble."
    )
    financial_info: Optional[FinancialSituation] = Field(
        default=None, 
        description="Situación financiera del usuario."
    )
    
    
class RouterToolModel(BaseModel):
    is_answer_name: bool = Field(
        default=False, 
        description="Indica si se le preguntado al usuario por su nombre"
    )
    
    
class VisitToolModel(BaseModel):
    selected_prop: Dict[int, Dict] = Field(
        default_factory=dict, 
        description="Inmueble seleccionado para la visita. Exclusivamente uno"
    )
    

class RAGToolModel(BaseModel):
    status: str = Field(
        default="", 
        description="Atributo de prueba"
    )

