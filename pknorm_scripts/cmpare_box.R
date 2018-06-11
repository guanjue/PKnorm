library(seewave)
library(MASS)
library(RColorBrewer)
library(ggplot2)
library(ggpubr)

files_list = list.files(pattern = "\\.all5info.txt$")


info_1 = read.table(files_list[1], header=TRUE, sep='\t')
info_type = colnames(info_1)
info_methods = rownames(info_1)


for (i in c(1:length(info_type))){
	info_matrix = c()
	for (j in c(1:length(files_list))){
		info_tmp = read.table(files_list[j], header=TRUE, sep='\t')[i]
		ct = unlist(strsplit(files_list[j], split='[.]'))[1]
		for (k in c(2:length(info_methods))){
			info_matrix = rbind(info_matrix, c(info_methods[k], info_tmp[k,]))
		}	
	}
	info_matrix = as.data.frame(info_matrix)
	colnames(info_matrix) = c('method', 'sig')
	info_matrix[,2] = apply(info_matrix, 1, function(x) as.numeric(x[2]))
	png(paste(info_type[i], '.box.png', sep=''), width=500, height=500)
	p = ggplot(data = info_matrix, aes(x=method, y=sig)) 
	p = p + geom_boxplot(aes(fill = method))
	p = p + geom_point(aes(y=sig, group=method), position = position_dodge(width=0.75))
	p = p + stat_compare_means(aes(group = method), label = "p.format", paired = TRUE, method = "t.test")
	plot(p)
	dev.off()
}









