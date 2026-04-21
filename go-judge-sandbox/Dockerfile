FROM criyle/go-judge:latest AS go-judge

# 第二阶段：构建实际运行环境
FROM debian:12-slim

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive

# 换源并安装 C++, Python, Java 环境
# 使用 Debian 12 默认源（或根据需要换成 mirrors.ustc.edu.cn）
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    g++ \
    python3 \
    openjdk-17-jdk-headless && \
    rm -rf /etc/java-21-openjdk && \
    cp -a /etc/java-17-openjdk /etc/java-21-openjdk && \
    mkdir -p /usr/local/jdk/jdk-25/bin && \
    ln -sf /usr/bin/java /usr/local/jdk/jdk-25/bin/java && \
    ln -sf /usr/bin/javac /usr/local/jdk/jdk-25/bin/javac && \
    rm -rf /var/lib/apt/lists/*

# 兼容教程中的 Java 目录写法
ENV JAVA_HOME=/usr/local/jdk/jdk-25
ENV PATH=$JAVA_HOME/bin:$PATH

WORKDIR /opt

# 从第一阶段拷贝 go-judge 程序及其默认配置
COPY --from=go-judge /opt/go-judge /opt/mount.yaml /opt/

# go-judge 默认挂载 /etc/java-21-openjdk，这里改为镜像内实际运行版本的配置目录
RUN sed -i 's#/etc/java-21-openjdk#/etc/java-17-openjdk#g' /opt/mount.yaml

# 暴露端口：5050 (HTTP), 5051 (gRPC), 5052 (Monitor)
EXPOSE 5050 5051 5052

# 启动命令：确保在 /opt 目录下执行
ENTRYPOINT ["./go-judge", "-http-addr", "0.0.0.0:5050"]