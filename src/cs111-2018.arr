################################################################
# CS111 Support functions
# Merges Bootstrap DS v2 and table-functions files
# Sept 2018

provide *
include tables 
include chart 
import statistics as S
import lists as L

# ----------- TABLE FUNCTIONS -----------

get-row :: (t :: Table, index :: Number) -> Row
fun get-row(t, index):
  t.row-n(index)
end

filter-by :: (t :: Table, test :: (Row -> Boolean)) -> Table
fun filter-by(t, test):
  t.filter(test)
end

sort-by :: (t :: Table, col :: String, sort-up :: Boolean) -> Table
fun sort-by(t, col, sort-up):
  t.order-by(col, sort-up)
end

build-column :: <A>(t :: Table, col :: String, builder :: (Row -> A)) -> Table
fun build-column(t, col, builder):
  t.build-column(col, builder)
end

add-row :: (t :: Table, r :: Row) -> Table
fun add-row(t, r): t.add-row(r) end

add-col :: (t :: Table, name :: String, c :: List<Any>) -> Table
fun add-col(t, name, c): t.add-column(name, c) end

select-columns :: (t :: Table, names :: List<String>) -> Table
fun select-columns(t, names): t.select-columns(names) end

transform-column :: <A, B>(t :: Table, name :: String, f :: (A -> B)) -> Table
fun transform-column(t, name, f): t.transform-column(name, f) end



# ----------- PLOTTING ------------------

# re-export render-chart
shadow render-chart = render-chart

# mean   :: (t :: Table, col :: String) -> Number
# median :: (t :: Table, col :: String) -> Number
# modes  :: (t :: Table, col :: String) -> List<Number>
# stdev  :: (t :: Table, col :: String) -> Number
fun mean(  t, col): S.mean(  t.column(col)) end
fun median(t, col): S.median(t.column(col)) end
fun modes( t, col): S.modes( t.column(col)) end
fun stdev( t, col): S.stdev( t.column(col)) end

# histogram :: (t :: Table, vals :: String, bin-width :: Number) -> Image
# scatter-plot :: (t :: Table, xs :: String, ys :: String) -> Image
# labeled-scatter-plot :: (t :: Table, xs :: String, ys :: String, ls :: String) -> Image
# pie-chart :: (t :: Table, ls :: String, vs :: String) -> Image
# bar-chart :: (t :: Table, ls :: String, vs :: String) -> Image
# dot-chart :: (t :: Table, vs :: String) -> Image
# box-plot :: (t :: Table, vs :: String) -> Image
# freq-bar-chart :: (t :: Table, vs :: String) -> Image
# lr-plot :: (t :: Table, xs :: String, ys :: String) -> Image
# labeled-lr-plot :: (t :: Table, ls :: String, xs :: String, ys :: String) -> Image
# function-plot :: (f :: (Number -> Number)) -> Image

fun histogram(t, vals, bin-width):
  doc: "wrap histogram so that the bin-width is set"
  if not(is-number(t.column(vals).get(0))):
    raise("Cannot make a histogram, because the '" + vals + "' column does not contain quantitative data")
  else:
  render-chart(from-list.histogram(t.column(vals)).bin-width(bin-width))
    .x-axis(vals)
    .y-axis("count")
    .display()
  end
end

fun scatter-plot(t, xs, ys):
  render-chart(from-list.scatter-plot(t.column(xs), t.column(ys)))
    .x-axis(xs)
    .y-axis(ys)
    .display()
end

fun labeled-scatter-plot(t, ls, xs, ys):
  render-chart(from-list.labeled-scatter-plot(t.column(ls), t.column(xs), t.column(ys)))
    .x-axis(xs)
    .y-axis(ys)
    .display()
end

fun pie-chart(t, ls, vs):
  render-chart(from-list.pie-chart(t.column(ls), t.column(vs))).display()
end

fun bar-chart(t, ls, vs):
  render-chart(from-list.bar-chart(t.column(ls), t.column(vs)))
    .y-axis(vs)
    .display()
end

fun dot-plot(t, vs):
  xs = t.column(vs)
  ys = L.repeat(xs.length(), 0)
  render-chart(from-list.scatter-plot(xs, ys)).x-axis(vs).display()
end

fun labeled-dot-plot(t, ls, vs):
  xs = t.column(vs)
  ys = L.repeat(xs.length(), 0)
  render-chart(from-list.labeled-scatter-plot(t.column(ls), xs, ys)).x-axis(vs).display()
end

fun box-plot(t, vs):
  render-chart(from-list.labeled-box-plot([list: vs], [list: t.column(vs)])).display()
end

fun freq-bar-chart(t, vs):
  values = t.column(vs).map(to-string)
  render-chart(from-list.freq-bar-chart(values))
    .x-axis(vs)
    .y-axis("count")
    .display()
end

fun lr-plot(t, xs, ys):
  scatter = from-list.scatter-plot(t.column(xs), t.column(ys))
  fn = S.linear-regression(t.column(xs), t.column(ys))
  fn-plot = from-list.function-plot(fn)
  r-sqr-str = num-to-string-digits(S.r-squared(t.column(xs), t.column(ys), fn), 3)
  alpha-str = num-to-string-digits(fn(2) - fn(1), 3)
  beta-str = num-to-string-digits(fn(0) * -1, 3)
  title-str = "y=" + alpha-str + "x + " + beta-str + ";     " + "r-sq: " + r-sqr-str
  render-charts([list: scatter, fn-plot]).title(title-str)
    .x-axis(xs)
    .y-axis(ys)
    .display()
end

fun labeled-lr-plot(t, ls, xs, ys):
  scatter = from-list.labeled-scatter-plot(t.column(ls), t.column(xs), t.column(ys))
  fn = S.linear-regression(t.column(xs), t.column(ys))
  fn-plot = from-list.function-plot(fn)
  r-sqr-str = num-to-string-digits(S.r-squared(t.column(xs), t.column(ys), fn), 3)
  alpha-str = num-to-string-digits(fn(2) - fn(1), 3)
  beta-str = num-to-string-digits(fn(0) * -1, 3)
  title-str = "y=" + alpha-str + "x + " + beta-str + ";     " + "r-sq: " + r-sqr-str
  render-charts([list: scatter, fn-plot]).title(title-str)
    .x-axis(xs)
    .y-axis(ys)
    .display()
end

fun function-plot(f):
  render-chart(from-list.function-plot(f))
    .x-axis("x")
    .y-axis("y")
    .display()
end

fun group(tab, col):
  values = list-to-list-set(tab.get-column(col)).to-list()
  for fold(grouped from table: value, subtable end, v from values):
    grouped.stack(table: value, subtable
        row: v, tab.filter-by(col, {(val): val == v})
      end)
  end
end

fun count(tab, col):
  order group(tab, col).build-column("count", {(r): r["subtable"].length()}).drop("subtable"): value ascending end
end

fun count-many(tab, cols):
  for fold(grouped from table: col, subtable end, c from cols):
    grouped.stack(table: col, subtable
        row: c, count(tab, c)
      end)
  end
end