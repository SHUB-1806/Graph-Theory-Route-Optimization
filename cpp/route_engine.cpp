#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <queue>
#include <random>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

struct City { int id; std::string name; double x, y; };
struct Edge { int u, v; double w; };
struct Arc { int to; double w; };

static const double INF = std::numeric_limits<double>::infinity();

static double distance(const City& a, const City& b) {
    const double dx = a.x - b.x, dy = a.y - b.y;
    return std::sqrt(dx * dx + dy * dy);
}

static bool save_graph(const std::string& dir, const std::vector<City>& cities,
                       const std::vector<Edge>& edges) {
    std::ofstream cf((dir + "/cities.csv").c_str());
    std::ofstream ef((dir + "/roads.csv").c_str());
    if (!cf || !ef) return false;
    cf << "id,name,x,y\n" << std::fixed << std::setprecision(4);
    for (size_t i = 0; i < cities.size(); ++i)
        cf << cities[i].id << ',' << cities[i].name << ',' << cities[i].x << ',' << cities[i].y << '\n';
    ef << "source,target,weight\n" << std::fixed << std::setprecision(3);
    for (size_t i = 0; i < edges.size(); ++i)
        ef << edges[i].u << ',' << edges[i].v << ',' << edges[i].w << '\n';
    return true;
}

static bool load_graph(const std::string& dir, std::vector<City>& cities,
                       std::vector<Edge>& edges) {
    std::ifstream cf((dir + "/cities.csv").c_str());
    std::ifstream ef((dir + "/roads.csv").c_str());
    if (!cf || !ef) return false;
    std::string line; std::getline(cf, line);
    while (std::getline(cf, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line); std::string part; City c;
        std::getline(ss, part, ','); c.id = std::atoi(part.c_str());
        std::getline(ss, c.name, ',');
        std::getline(ss, part, ','); c.x = std::atof(part.c_str());
        std::getline(ss, part, ','); c.y = std::atof(part.c_str());
        cities.push_back(c);
    }
    std::getline(ef, line);
    while (std::getline(ef, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line); std::string part; Edge e;
        std::getline(ss, part, ','); e.u = std::atoi(part.c_str());
        std::getline(ss, part, ','); e.v = std::atoi(part.c_str());
        std::getline(ss, part, ','); e.w = std::atof(part.c_str());
        edges.push_back(e);
    }
    return !cities.empty();
}

static void generate(int n, unsigned seed, std::vector<City>& cities, std::vector<Edge>& edges) {
    std::mt19937 rng(seed);
    std::uniform_real_distribution<double> jitter(-5.0, 5.0), noise(0.92, 1.25);
    // Nine broad regions create natural-looking city clusters without disconnecting the network.
    const double centers[9][2] = {{12,14},{36,12},{65,13},{87,20},{18,48},{48,43},{79,49},{30,78},{68,79}};
    cities.reserve(n);
    for (int i = 0; i < n; ++i) {
        int region = i % 9;
        double angle = (i / 9) * 2.399963229728653; // golden angle
        double radius = 2.0 + std::fmod((i / 9) * 1.71, 14.0);
        City c;
        c.id = i; c.name = "City_" + std::to_string(i + 1);
        c.x = std::max(2.0, std::min(98.0, centers[region][0] + std::cos(angle) * radius + jitter(rng)));
        c.y = std::max(3.0, std::min(97.0, centers[region][1] + std::sin(angle) * radius * .70 + jitter(rng)));
        cities.push_back(c);
    }
    std::vector<std::vector<bool> > linked(n, std::vector<bool>(n, false));
    // Connect every city to its nearest predecessors: guaranteed connected, sparse, and geographic.
    for (int i = 1; i < n; ++i) {
        std::vector<std::pair<double,int> > candidates;
        for (int j = 0; j < i; ++j) candidates.push_back(std::make_pair(distance(cities[i], cities[j]), j));
        std::sort(candidates.begin(), candidates.end());
        int links = std::min(i, 3);
        for (int k = 0; k < links; ++k) {
            int j = candidates[k].second;
            if (!linked[i][j]) {
                double w = candidates[k].first * noise(rng) + 1.0;
                edges.push_back(Edge{i, j, w}); linked[i][j] = linked[j][i] = true;
            }
        }
    }
    // Add a few express roads to avoid an overly local lattice.
    std::uniform_int_distribution<int> pick(0, n - 1);
    for (int k = 0; k < n / 2; ++k) {
        int u = pick(rng), v = pick(rng);
        if (u == v || linked[u][v]) continue;
        double d = distance(cities[u], cities[v]);
        if (d < 12.0 || d > 42.0) continue;
        edges.push_back(Edge{u, v, d * noise(rng) + 1.0}); linked[u][v] = linked[v][u] = true;
    }
}

static int shortest_path(int source, int target, int n, const std::vector<Edge>& edges,
                         std::vector<int>& path, double& total) {
    if (source < 0 || target < 0 || source >= n || target >= n) return 2;
    std::vector<std::vector<Arc> > graph(n);
    for (size_t i = 0; i < edges.size(); ++i) {
        graph[edges[i].u].push_back(Arc{edges[i].v, edges[i].w});
        graph[edges[i].v].push_back(Arc{edges[i].u, edges[i].w});
    }
    std::vector<double> dist(n, INF); std::vector<int> prev(n, -1);
    typedef std::pair<double,int> State;
    std::priority_queue<State, std::vector<State>, std::greater<State> > pq;
    dist[source] = 0.0; pq.push(State(0.0, source));
    while (!pq.empty()) {
        State cur = pq.top(); pq.pop();
        double d = cur.first; int u = cur.second;
        if (d != dist[u]) continue;
        if (u == target) break;
        for (size_t i = 0; i < graph[u].size(); ++i) {
            Arc a = graph[u][i]; double nd = d + a.w;
            if (nd < dist[a.to]) { dist[a.to] = nd; prev[a.to] = u; pq.push(State(nd, a.to)); }
        }
    }
    if (!std::isfinite(dist[target])) return 3;
    for (int at = target; at != -1; at = prev[at]) path.push_back(at);
    std::reverse(path.begin(), path.end()); total = dist[target]; return 0;
}

static void usage() {
    std::cerr << "Usage:\n  route_engine generate <output_dir> [cities=500] [seed=42]\n"
              << "  route_engine path <data_dir> <source_id> <target_id>\n"
              << "  route_engine stats <data_dir>\n";
}

int main(int argc, char** argv) {
    if (argc < 3) { usage(); return 1; }
    const std::string command = argv[1], dir = argv[2];
    std::vector<City> cities; std::vector<Edge> edges;
    if (command == "generate") {
        int n = argc > 3 ? std::atoi(argv[3]) : 500; unsigned seed = argc > 4 ? (unsigned)std::atoi(argv[4]) : 42;
        if (n < 2 || n > 10000) { std::cerr << "City count must be between 2 and 10000.\n"; return 2; }
        generate(n, seed, cities, edges);
        if (!save_graph(dir, cities, edges)) { std::cerr << "Could not write graph data.\n"; return 3; }
        std::cout << "generated," << cities.size() << ',' << edges.size() << '\n'; return 0;
    }
    if (!load_graph(dir, cities, edges)) { std::cerr << "Could not load cities.csv and roads.csv.\n"; return 3; }
    if (command == "path") {
        if (argc < 5) { usage(); return 1; }
        std::vector<int> path; double total = 0.0;
        int result = shortest_path(std::atoi(argv[3]), std::atoi(argv[4]), (int)cities.size(), edges, path, total);
        if (result) { std::cerr << (result == 2 ? "Invalid city id.\n" : "No route exists.\n"); return result; }
        std::cout << std::fixed << std::setprecision(3) << "distance," << total << "\npath";
        for (size_t i = 0; i < path.size(); ++i) std::cout << ',' << path[i];
        std::cout << '\n'; return 0;
    }
    if (command == "stats") {
        std::vector<int> degree(cities.size(), 0);
        double sum = 0.0, lo = INF, hi = 0.0;
        for (size_t i = 0; i < edges.size(); ++i) { ++degree[edges[i].u]; ++degree[edges[i].v]; sum += edges[i].w; lo = std::min(lo, edges[i].w); hi = std::max(hi, edges[i].w); }
        std::cout << std::fixed << std::setprecision(3) << "cities," << cities.size() << "\nroads," << edges.size()
                  << "\navg_degree," << (2.0 * edges.size() / cities.size()) << "\nmin_weight," << lo
                  << "\nmax_weight," << hi << "\navg_weight," << (sum / edges.size()) << '\n'; return 0;
    }
    usage(); return 1;
}
