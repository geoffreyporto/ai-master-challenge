/** Formatação pt-BR e paleta — as mesmas do relatório, para o painel não
 *  contar a história com outras cores nem com outra pontuação decimal. */

const PALETA = {
  azul: "#2a78d6",
  laranja: "#eb6834",
  tinta: "#1b1b1a",
  tinta2: "#55534e",
  suave: "#a8a5a0",
  grade: "#e6e4e0",
  bom: "#2f7d4f",
  ruim: "#c0392b",
};

function br(valor: number, casas = 1): string {
  return valor.toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

function brAuto(valor: number): string {
  if (!isFinite(valor)) return "—";
  if (Number.isInteger(valor)) return valor.toLocaleString("pt-BR");
  return br(valor, Math.abs(valor) < 10 ? 2 : 1);
}

function dinheiro(valor: number): string {
  return "US$ " + valor.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
}

function mesCurto(iso: string): string {
  const meses = [
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
  ];
  const d = new Date(iso + "T00:00:00");
  return meses[d.getMonth()] + "/" + String(d.getFullYear()).slice(2);
}
